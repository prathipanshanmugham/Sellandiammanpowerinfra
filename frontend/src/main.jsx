import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, HashRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
// Latin and latin-ext (for ₹) only; Tamil loads when Tamil text is on screen.
import "@fontsource/montserrat/latin-700.css";
import "@fontsource/montserrat/latin-800.css";
import "@fontsource/montserrat/latin-ext-700.css";
import "@fontsource/montserrat/latin-ext-800.css";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-ext-400.css";
import "@fontsource/inter/latin-ext-500.css";
import "@fontsource/inter/latin-ext-600.css";
import "@fontsource/noto-sans-tamil/tamil-400.css";
import "@fontsource/noto-sans-tamil/tamil-600.css";
import "./index.css";
import { IS_DEMO } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import { SiteProvider } from "@/components/public/site";
import App from "./App";

const qc = new QueryClient({ defaultOptions: { queries: { retry: (n, e) => n < 1 && ![401, 403, 404].includes(e?.response?.status), refetchOnWindowFocus: false } } });

async function boot() {
  // The hosted preview runs the whole app in the browser against sample data (no server).
  // (import.meta.env is replaced at build time, so the live site leaves the preview code out entirely)
  if (import.meta.env.VITE_DEMO === "true") await (await import("./demo/boot")).default();
  const Router = IS_DEMO ? HashRouter : BrowserRouter;
  ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <QueryClientProvider client={qc}>
          <AuthProvider>
            <SiteProvider>
              <App />
              <Toaster position="bottom-center" richColors closeButton toastOptions={{ style: { fontFamily: "Inter, sans-serif" } }} />
            </SiteProvider>
          </AuthProvider>
        </QueryClientProvider>
      </Router>
    </React.StrictMode>,
  );
}
boot();
