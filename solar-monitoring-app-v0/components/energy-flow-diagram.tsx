"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ParticleFlowDiagram } from "./flows/particle-flow"
import { RadialFlowDiagram } from "./flows/radial-flow"
import { SankeyFlowDiagram } from "./flows/sankey-flow"

type FlowStyle = "particle" | "radial" | "sankey"

export function EnergyFlowDiagram() {
  const [flowStyle, setFlowStyle] = useState<FlowStyle>("particle")

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-medium text-foreground">Live Energy Flow</CardTitle>
          <div className="flex gap-1">
            <Button
              variant={flowStyle === "particle" ? "default" : "ghost"}
              size="sm"
              onClick={() => setFlowStyle("particle")}
              className="text-xs h-7"
            >
              Particle
            </Button>
            <Button
              variant={flowStyle === "radial" ? "default" : "ghost"}
              size="sm"
              onClick={() => setFlowStyle("radial")}
              className="text-xs h-7"
            >
              Radial
            </Button>
            <Button
              variant={flowStyle === "sankey" ? "default" : "ghost"}
              size="sm"
              onClick={() => setFlowStyle("sankey")}
              className="text-xs h-7"
            >
              Sankey
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {flowStyle === "particle" && <ParticleFlowDiagram />}
        {flowStyle === "radial" && <RadialFlowDiagram />}
        {flowStyle === "sankey" && <SankeyFlowDiagram />}
      </CardContent>
    </Card>
  )
}
