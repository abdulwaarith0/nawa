import { ApiError } from "@nawa/api-client";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithLocale } from "../../components/test-utils";
import { LoginForm } from "./LoginForm";

const login = vi.fn();
vi.mock("../../lib/apiClient", () => ({
  getApiClient: () => ({ auth: { login } }),
}));

describe("LoginForm", () => {
  const assign = vi.fn();

  beforeEach(() => {
    login.mockReset();
    assign.mockReset();
    vi.stubGlobal("location", { search: "", assign, pathname: "/login" });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("renders localized labels under en", () => {
    renderWithLocale(<LoginForm />, "en");
    expect(screen.getByRole("heading", { name: "Sign in to NAWA" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email, username, or phone")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders Arabic labels under ar", () => {
    renderWithLocale(<LoginForm />, "ar");
    expect(screen.getByRole("heading", { name: "تسجيل الدخول إلى نواة" })).toBeInTheDocument();
  });

  it("submits credentials and navigates home on success", async () => {
    login.mockResolvedValue({ id: "1" });
    renderWithLocale(<LoginForm />, "en");
    await userEvent.type(screen.getByLabelText("Email, username, or phone"), "admin@nawa.local");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(login).toHaveBeenCalledWith("admin@nawa.local", "password"));
    expect(assign).toHaveBeenCalledWith("/");
  });

  it("redirects to the ?next target when present and same-origin", async () => {
    vi.stubGlobal("location", { search: "?next=%2Fintake", assign, pathname: "/login" });
    login.mockResolvedValue({ id: "1" });
    renderWithLocale(<LoginForm />, "en");
    await userEvent.type(screen.getByLabelText("Email, username, or phone"), "a@x.com");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/intake"));
  });

  it("shows a generic error and stays on the page when login fails", async () => {
    login.mockRejectedValue(new ApiError(401, 401, "Authentication required"));
    renderWithLocale(<LoginForm />, "en");
    await userEvent.type(screen.getByLabelText("Email, username, or phone"), "bad");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByText("Sign in failed. Check your details and try again."),
    ).toBeInTheDocument();
    expect(assign).not.toHaveBeenCalled();
  });
});
