import type { ReactNode } from "react";

export default function ErrorNotice({ children }: { children: ReactNode }) {
  return (
    <div className="error-notice" role="alert">
      <span className="error-notice-label mono">ERROR</span>
      <p>{children}</p>
    </div>
  );
}
