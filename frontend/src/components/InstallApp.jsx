import { useState } from "react";
import { Download, MoreVertical, Share, SquarePlus, Menu as MenuIcon, Check } from "lucide-react";
import { Dialog } from "@/components/ui/kit";
import { APPS, appFor, promptInstall, useInstall } from "@/lib/pwa";

// Steps for each browser when it doesn't offer its own install dialog (iPhone always; Android before the offer arrives)
const STEPS = {
  ios: [[Share, "Tap the Share button in Safari's toolbar (the square with an arrow)."], [SquarePlus, "Scroll down and tap “Add to Home Screen”."], [Check, "Tap “Add”. The app opens full screen from your home screen."]],
  "ios-other": [[Share, "Tap the Share button next to the address bar."], [SquarePlus, "Tap “Add to Home Screen”. If you don't see it, open this page in Safari."], [Check, "Tap “Add”. The app opens full screen from your home screen."]],
  android: [[MoreVertical, "Tap the browser menu (⋮) at the top right."], [Download, "Tap “Install app” (or “Add to Home screen”, then “Install”)."], [Check, "The app appears on your home screen and in your app list."]],
  samsung: [[MenuIcon, "Tap the menu (☰) at the bottom right."], [SquarePlus, "Tap “Add page to”, then “Home screen”."], [Check, "The app appears on your home screen."]],
  firefox: [[MoreVertical, "Tap the browser menu (⋮)."], [Download, "Tap “Install” (or “Add to Home screen”)."], [Check, "The app appears on your home screen."]],
  desktop: [[Download, "Click the install icon at the right end of the address bar, or open the browser menu and choose “Install”."], [Check, "The app opens in its own window and from your apps list."]],
};

// Install entry points share one flow: the browser's own dialog when it has one, otherwise the steps for this browser.
// `start()` opens it; render `dialog` once near the button. `show` is false once the app is installed.
export function useInstallFlow(pathname = typeof window !== "undefined" ? window.location.pathname : "/") {
  const st = useInstall();
  const [open, setOpen] = useState(false);
  const app = APPS[appFor(pathname)];
  const start = async () => {
    const r = await promptInstall();
    if (r === "manual") setOpen(true);
  };
  const steps = STEPS[st.platform] || STEPS.android;
  const dialog = (
    <Dialog open={open} onOpenChange={setOpen} title={`Install ${app.name}`} description="Use it like any other app: its own icon on your home screen, full screen, no address bar.">
      <ol className="space-y-3">
        {steps.map(([Ic, text], n) => (
          <li key={n} className="flex gap-3 text-[15px] leading-snug">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-fg/5 text-fg"><Ic className="h-4 w-4" aria-hidden="true" /></span>
            <span className="pt-1.5"><span className="sr-only">Step {n + 1}: </span>{text}</span>
          </li>
        ))}
      </ol>
    </Dialog>
  );
  return { show: st.show, installed: st.installed, start, dialog, appName: app.name };
}

// A ready-made button for pages and menus
export function InstallAppButton({ className, label = "Install the app", pathname }) {
  const flow = useInstallFlow(pathname);
  if (!flow.show) return null;
  return (
    <>
      <button type="button" onClick={flow.start} className={className}>
        <Download className="h-4 w-4 shrink-0" aria-hidden="true" />{label}
      </button>
      {flow.dialog}
    </>
  );
}
