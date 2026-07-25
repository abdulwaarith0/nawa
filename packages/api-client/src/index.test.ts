import { describe, expect, it, vi } from "vitest";
import { ApiError, createApiClient } from "./index.js";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("createApiClient", () => {
  it("unwraps the envelope's data on 2xx", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { code: 200, message: "OK", data: { hello: "world" } }));
    const client = createApiClient({ baseUrl: "http://api", fetchImpl });
    const data = await client.get<{ hello: string }>("/thing");
    expect(data).toEqual({ hello: "world" });
  });

  it("throws ApiError with status/code/message on non-2xx", async () => {
    // fresh Response per call — a body can only be read once.
    const fetchImpl = vi
      .fn()
      .mockImplementation(async () =>
        jsonResponse(404, { code: 404, message: "Not found", data: null }),
      );
    const client = createApiClient({ baseUrl: "http://api", fetchImpl });
    await expect(client.get("/missing")).rejects.toMatchObject({
      status: 404,
      code: 404,
      message: "Not found",
    });
    await expect(client.get("/missing")).rejects.toBeInstanceOf(ApiError);
  });

  it("synthesizes an envelope for a non-JSON body", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response("upstream exploded", { status: 502 }));
    const client = createApiClient({ baseUrl: "http://api", fetchImpl });
    await expect(client.get("/x")).rejects.toMatchObject({
      status: 502,
      message: "upstream exploded",
    });
  });

  it("adds the bearer header when a token getter returns one", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { code: 200, message: "OK", data: null }));
    const client = createApiClient({
      baseUrl: "http://api",
      getAccessToken: () => "tok-123",
      fetchImpl,
    });
    await client.get("/x");
    const init = fetchImpl.mock.calls[0]?.[1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok-123");
  });

  it("retries once after a 401 when refresh succeeds", async () => {
    const fetchImpl = vi
      .fn()
      // first the protected call → 401
      .mockResolvedValueOnce(jsonResponse(401, { code: 401, message: "no", data: null }))
      // then the refresh → new tokens
      .mockResolvedValueOnce(
        jsonResponse(200, {
          code: 200,
          message: "OK",
          data: { access_token: "new", refresh_token: "r2", expires_in: 900 },
        }),
      )
      // then the replayed protected call → 200
      .mockResolvedValueOnce(jsonResponse(200, { code: 200, message: "OK", data: { ok: true } }));

    const onTokens = vi.fn();
    const client = createApiClient({
      baseUrl: "http://api",
      getRefreshToken: () => "r1",
      onTokens,
      fetchImpl,
    });
    const data = await client.get<{ ok: boolean }>("/protected");
    expect(data).toEqual({ ok: true });
    expect(onTokens).toHaveBeenCalledWith({
      access_token: "new",
      refresh_token: "r2",
      expires_in: 900,
    });
    expect(fetchImpl).toHaveBeenCalledTimes(3);
  });

  it("does not loop: a second 401 after refresh throws instead of retrying again", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { code: 401, message: "no", data: null }))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          code: 200,
          message: "OK",
          data: { access_token: "new", refresh_token: "r2", expires_in: 900 },
        }),
      )
      .mockResolvedValueOnce(jsonResponse(401, { code: 401, message: "still no", data: null }));

    const onAuthError = vi.fn();
    const client = createApiClient({
      baseUrl: "http://api",
      getRefreshToken: () => "r1",
      onAuthError,
      fetchImpl,
    });
    await expect(client.get("/protected")).rejects.toMatchObject({ status: 401 });
    expect(onAuthError).toHaveBeenCalledOnce();
    expect(fetchImpl).toHaveBeenCalledTimes(3);
  });

  it("calls onAuthError when refresh fails", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { code: 401, message: "no", data: null }))
      .mockResolvedValueOnce(
        jsonResponse(401, { code: 401, message: "refresh denied", data: null }),
      );

    const onAuthError = vi.fn();
    const client = createApiClient({ baseUrl: "http://api", onAuthError, fetchImpl });
    await expect(client.get("/protected")).rejects.toMatchObject({ status: 401 });
    expect(onAuthError).toHaveBeenCalledOnce();
  });

  it("posts FormData bodies untouched, without a JSON Content-Type", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(jsonResponse(202, { code: 202, message: "Accepted", data: { ok: true } }));
    const client = createApiClient({ baseUrl: "http://api", fetchImpl });

    const form = new FormData();
    form.append("file", new Blob(["x"]), "a.csv");
    const data = await client.post("/uploads", form);

    expect(data).toEqual({ ok: true });
    const [, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(form);
    expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
  });

  it("auth.requestAccess posts to /auth/request-access with the given input", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { code: 200, message: "OK", data: null }));
    const client = createApiClient({ baseUrl: "http://api", fetchImpl });
    const input = { full_name: "Alice", email: "alice@example.com", reason: "join" };
    await client.auth.requestAccess(input);

    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api/auth/request-access");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual(input);
  });

  it("de-dupes concurrent 401s through a single refresh", async () => {
    let refreshCalls = 0;
    const fetchImpl = vi.fn(async (url: string, _init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        refreshCalls += 1;
        // slow refresh so both requests overlap on it
        await new Promise((r) => setTimeout(r, 10));
        return jsonResponse(200, {
          code: 200,
          message: "OK",
          data: { access_token: "new", refresh_token: "r2", expires_in: 900 },
        });
      }
      // both protected calls: 401 first time each, then 200 after refresh
      return jsonResponse(200, { code: 200, message: "OK", data: { ok: true } });
    });

    // Force both initial protected calls to 401.
    let firstA = true;
    let firstB = true;
    const fetchWith401 = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/a") && firstA) {
        firstA = false;
        return jsonResponse(401, { code: 401, message: "no", data: null });
      }
      if (url.endsWith("/b") && firstB) {
        firstB = false;
        return jsonResponse(401, { code: 401, message: "no", data: null });
      }
      return fetchImpl(url, init);
    });

    const client = createApiClient({
      baseUrl: "http://api",
      getRefreshToken: () => "r1",
      fetchImpl: fetchWith401 as unknown as typeof fetch,
    });
    const [ra, rb] = await Promise.all([client.get("/a"), client.get("/b")]);
    expect(ra).toEqual({ ok: true });
    expect(rb).toEqual({ ok: true });
    expect(refreshCalls).toBe(1); // one shared refresh, not two
  });
});
