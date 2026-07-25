import { LoginWrapper } from "@/libs";
import { renderWithLocale } from "@/test/test-utils";
import { ApiError } from "@nawa/api-client";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const login = vi.fn();
vi.mock("@/lib/apiClient", () => ({
  getApiClient: () => ({ auth: { login } }),
}));

describe("LoginWrapper", () => {
  const assign = vi.fn();

  beforeEach(() => {
    login.mockReset();
    assign.mockReset();
    vi.stubGlobal("location", { search: "", assign, pathname: "/login" });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("renders localized labels under en", () => {
    renderWithLocale(<LoginWrapper />, "en");
    expect(screen.getByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getByLabelText("Work email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders Arabic labels under ar", () => {
    renderWithLocale(<LoginWrapper />, "ar");
    expect(screen.getByRole("heading", { name: "مرحبًا بعودتك" })).toBeInTheDocument();
  });

  it("submits credentials and navigates to the account's permission-based home on success", async () => {
    login.mockResolvedValue({ id: "1", effective: ["nawa:console:intake"] });
    renderWithLocale(<LoginWrapper />, "en");
    await userEvent.type(screen.getByLabelText("Work email"), "admin@nawa.local");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(login).toHaveBeenCalledWith("admin@nawa.local", "password"));
    expect(assign).toHaveBeenCalledWith("/intake");
  });

  it("redirects to the ?next target when present and same-origin, even over the permission-based home", async () => {
    vi.stubGlobal("location", { search: "?next=%2Fintake", assign, pathname: "/login" });
    login.mockResolvedValue({ id: "1", effective: ["nawa:console:admin"] });
    renderWithLocale(<LoginWrapper />, "en");
    await userEvent.type(screen.getByLabelText("Work email"), "a@x.com");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/intake"));
  });

  it("toggles password visibility", async () => {
    renderWithLocale(<LoginWrapper />, "en");
    const password = screen.getByLabelText("Password");
    expect(password).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(password).toHaveAttribute("type", "text");
    await userEvent.click(screen.getByRole("button", { name: "Hide password" }));
    expect(password).toHaveAttribute("type", "password");
  });

  it("shows a generic error and stays on the page when login fails", async () => {
    login.mockRejectedValue(new ApiError(401, 401, "Authentication required"));
    renderWithLocale(<LoginWrapper />, "en");
    await userEvent.type(screen.getByLabelText("Work email"), "bad");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByText("Sign in failed. Check your details and try again."),
    ).toBeInTheDocument();
    expect(assign).not.toHaveBeenCalled();
  });
});
