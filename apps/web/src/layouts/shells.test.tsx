import { AuthShell, LocaleSwitcher, TopNav, setLocaleCookie } from "@/layouts";
import { renderWithLocale } from "@/test/test-utils";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the session hook so TopNav/AuthShell can be tested signed-out vs signed-in.
const mockUseSession = vi.fn();
vi.mock("@/hooks/Auth", () => ({
  useSession: () => mockUseSession(),
}));

const logout = vi.fn().mockResolvedValue(undefined);
vi.mock("@/lib/apiClient", () => ({
  getApiClient: () => ({ auth: { logout } }),
}));

const routerReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: routerReplace, push: vi.fn() }),
}));

describe("LocaleSwitcher", () => {
  beforeEach(() => {
    // reset cookies
    document.cookie = "nw_locale=; path=/; max-age=0";
  });

  it("shows EN when the current locale is Arabic", () => {
    renderWithLocale(<LocaleSwitcher />, "ar");
    expect(screen.getByRole("button", { name: "Switch to English" })).toHaveTextContent("EN");
  });

  it("shows the Arabic label when the current locale is English", () => {
    renderWithLocale(<LocaleSwitcher />, "en");
    expect(screen.getByRole("button", { name: "التبديل إلى العربية" })).toHaveTextContent("ع");
  });

  it("setLocaleCookie writes the nw_locale cookie", () => {
    setLocaleCookie("en");
    expect(document.cookie).toContain("nw_locale=en");
  });
});

describe("TopNav", () => {
  const reloadSpy = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("location", { pathname: "/", reload: reloadSpy, href: "" });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    mockUseSession.mockReset();
  });

  it("shows Sign in + Apply when signed out", () => {
    mockUseSession.mockReturnValue({ user: null, isSignedIn: false });
    renderWithLocale(<TopNav />, "en");
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apply" })).toBeInTheDocument();
    expect(screen.getByText("NAWA")).toBeInTheDocument();
  });

  it("shows the member avatar + sign-out (not auth actions) when signed in", () => {
    mockUseSession.mockReturnValue({
      user: {
        id: "1",
        username: "ahmed",
        full_name: "Ahmed Al-Sayed",
        email: "a@x.com",
        language: "ar",
        is_active: true,
        effective: [],
      },
      isSignedIn: true,
    });
    renderWithLocale(<TopNav />, "en");
    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/dashboard");
    expect(screen.getByRole("img", { name: "Ahmed Al-Sayed" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });

  it("sign-out calls logout then navigates home", async () => {
    mockUseSession.mockReturnValue({
      user: {
        id: "1",
        username: "ahmed",
        full_name: "Ahmed",
        email: "a@x.com",
        language: "en",
        is_active: true,
        effective: [],
      },
      isSignedIn: true,
    });
    const assign = vi.fn();
    vi.stubGlobal("location", { pathname: "/", reload: vi.fn(), href: "", assign });
    renderWithLocale(<TopNav />, "en");
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(logout).toHaveBeenCalled();
    expect(assign).toHaveBeenCalledWith("/");
  });

  it("locale switch triggers a reload after setting the cookie", async () => {
    mockUseSession.mockReturnValue({ user: null, isSignedIn: false });
    renderWithLocale(<TopNav />, "ar");
    await userEvent.click(screen.getByRole("button", { name: "Switch to English" }));
    expect(document.cookie).toContain("nw_locale=en");
    expect(reloadSpy).toHaveBeenCalled();
  });
});

describe("AuthShell", () => {
  afterEach(() => {
    mockUseSession.mockReset();
    routerReplace.mockReset();
  });

  it("renders the wordmark, a locale switcher, and its children when signed out", () => {
    mockUseSession.mockReturnValue({ isLoading: false, isSignedIn: false });
    // Rendered under ar, so the switcher offers English.
    renderWithLocale(
      <AuthShell storyKey="login">
        <p>child content</p>
      </AuthShell>,
      "ar",
    );
    expect(screen.getByText("Nawa")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Switch to English" })).toBeInTheDocument();
    expect(screen.getByText("child content")).toBeInTheDocument();
  });

  it("shows a loading state instead of the form while the session resolves", () => {
    mockUseSession.mockReturnValue({ isLoading: true, isSignedIn: false });
    renderWithLocale(
      <AuthShell storyKey="login">
        <p>child content</p>
      </AuthShell>,
      "en",
    );
    expect(screen.queryByText("child content")).not.toBeInTheDocument();
    expect(routerReplace).not.toHaveBeenCalled();
  });

  it("bounces an already-signed-in user to their permission-based home instead of flashing the form", () => {
    mockUseSession.mockReturnValue({
      isLoading: false,
      isSignedIn: true,
      user: { effective: ["nawa:console:intake"] },
    });
    renderWithLocale(
      <AuthShell storyKey="login">
        <p>child content</p>
      </AuthShell>,
      "en",
    );
    expect(screen.queryByText("child content")).not.toBeInTheDocument();
    expect(routerReplace).toHaveBeenCalledWith("/intake");
  });
});
