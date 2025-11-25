import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function LoadingSpinner({ className, ...props }) {
  return (
    <Loader2
      className={cn("h-6 w-6 animate-spin text-primary", className)}
      {...props}
    />
  );
}

export function FullPageLoadingSpinner() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <LoadingSpinner className="h-12 w-12" />
    </div>
  );
}

export const LoadingOverlay = FullPageLoadingSpinner;
