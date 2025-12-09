"use client"

import { Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface TimeRangeSelectorProps {
  value: string
  onChange: (value: string) => void
}

const options = [
  { value: "today", label: "Today" },
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
  { value: "year", label: "Year" },
]

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="flex items-center gap-1 p-1 bg-card rounded-lg border border-border">
      {options.map((option) => (
        <Button
          key={option.value}
          variant="ghost"
          size="sm"
          onClick={() => onChange(option.value)}
          className={cn(
            "h-8 px-3 text-sm",
            value === option.value
              ? "bg-primary text-primary-foreground hover:bg-primary/90"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option.label}
        </Button>
      ))}
      <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
        <Calendar className="h-4 w-4" />
      </Button>
    </div>
  )
}
