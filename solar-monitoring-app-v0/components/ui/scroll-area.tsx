"use client"

import type * as React from "react"

import { cn } from "@/lib/utils"

// <CHANGE> Replaced Radix ScrollArea with native scrollable div to avoid RTL CSS parsing errors
function ScrollArea({ className, children, ...props }: React.ComponentProps<"div">) {
  return (
    <div data-slot="scroll-area" className={cn("relative overflow-auto", className)} {...props}>
      {children}
    </div>
  )
}

function ScrollBar({
  className,
  orientation = "vertical",
  ...props
}: React.ComponentProps<"div"> & {
  orientation?: "vertical" | "horizontal"
}) {
  return null // Native scrollbars are used instead
}

export { ScrollArea, ScrollBar }
