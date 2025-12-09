import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Progress } from './ui/progress'
import { Receipt, TrendingDown, ArrowRight, Leaf } from 'lucide-react'

export function BillingCard() {
  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-medium text-foreground">Billing Summary</CardTitle>
          <Receipt className="h-5 w-5 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Current Bill */}
        <div className="p-4 rounded-lg bg-secondary/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">Current Month</span>
            <span className="text-xs text-emerald-400 flex items-center gap-1">
              <TrendingDown className="h-3 w-3" />
              -42% vs last month
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-semibold text-foreground">$47.20</span>
            <span className="text-muted-foreground">estimated</span>
          </div>
        </div>

        {/* Credits */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">Export Credits</span>
            <span className="text-sm font-medium text-emerald-400">+$124.80</span>
          </div>
          <Progress value={75} className="h-2 bg-secondary" />
          <p className="text-xs text-muted-foreground mt-1">520 kWh exported this month</p>
        </div>

        {/* Savings */}
        <div className="p-4 rounded-lg bg-emerald-400/10 border border-emerald-400/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-emerald-400/20">
              <Leaf className="h-4 w-4 text-emerald-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">Total Savings</p>
              <p className="text-xs text-muted-foreground">Since installation</p>
            </div>
          </div>
          <p className="text-2xl font-semibold text-emerald-400 mt-3">$4,892.50</p>
        </div>

        {/* Rate Info */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Import Rate</span>
            <span className="text-foreground">$0.28/kWh</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Export Rate</span>
            <span className="text-foreground">$0.24/kWh</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Peak Hours</span>
            <span className="text-foreground">2PM - 7PM</span>
          </div>
        </div>

        <Button variant="outline" className="w-full bg-transparent">
          View Full Billing
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </CardContent>
    </Card>
  )
}

