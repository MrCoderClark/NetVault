import * as React from "react";

import { cn } from "@/lib/utils";

function Card({ className, ...props }: React.ComponentProps<"section">) {
  return <section className={cn("panel", className)} {...props} />;
}

export { Card };
