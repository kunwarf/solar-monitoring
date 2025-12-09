import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Receipt,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Calendar,
  Download,
  CreditCard,
  Leaf,
  ArrowRight,
} from "lucide-react"

const billingHistory = [
  { month: "November 2024", import: 145, export: 312, cost: 21.75, credit: 46.8, net: -25.05 },
  { month: "October 2024", import: 168, export: 298, cost: 25.2, credit: 44.7, net: -19.5 },
  { month: "September 2024", import: 132, export: 345, cost: 19.8, credit: 51.75, net: -31.95 },
  { month: "August 2024", import: 156, export: 378, cost: 23.4, credit: 56.7, net: -33.3 },
]

export default function BillingPage() {
  return (
    <div className="flex-1 p-6 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Billing & Savings</h1>
          <p className="text-muted-foreground">Track your energy costs and earnings</p>
        </div>
        <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export Report
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <DollarSign className="h-5 w-5 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">This Month</p>
                <p className="text-2xl font-bold text-green-500">-$25.05</p>
                <p className="text-xs text-muted-foreground">Credit balance</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-500/20">
                <TrendingUp className="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Export Earnings</p>
                <p className="text-2xl font-bold text-foreground">$46.80</p>
                <p className="text-xs text-green-500">+5% vs last month</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/20">
                <TrendingDown className="h-5 w-5 text-red-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Import Cost</p>
                <p className="text-2xl font-bold text-foreground">$21.75</p>
                <p className="text-xs text-green-500">-14% vs last month</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/20">
                <Leaf className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Yearly Savings</p>
                <p className="text-2xl font-bold text-foreground">$1,245</p>
                <p className="text-xs text-muted-foreground">Since Jan 2024</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Current Bill */}
        <Card className="col-span-2 bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Receipt className="h-5 w-5" />
              Current Billing Period
            </CardTitle>
            <CardDescription>November 1 - November 30, 2024</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Energy Flow Summary */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                <div className="flex items-center gap-2 text-red-400 mb-2">
                  <TrendingDown className="h-4 w-4" />
                  <span className="text-sm font-medium">Grid Import</span>
                </div>
                <p className="text-2xl font-bold text-foreground">145 kWh</p>
                <p className="text-sm text-muted-foreground">@ $0.15/kWh</p>
                <p className="text-lg font-semibold text-red-400 mt-2">$21.75</p>
              </div>
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                <div className="flex items-center gap-2 text-green-500 mb-2">
                  <TrendingUp className="h-4 w-4" />
                  <span className="text-sm font-medium">Grid Export</span>
                </div>
                <p className="text-2xl font-bold text-foreground">312 kWh</p>
                <p className="text-sm text-muted-foreground">@ $0.15/kWh</p>
                <p className="text-lg font-semibold text-green-500 mt-2">$46.80</p>
              </div>
              <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <div className="flex items-center gap-2 text-blue-500 mb-2">
                  <DollarSign className="h-4 w-4" />
                  <span className="text-sm font-medium">Net Balance</span>
                </div>
                <p className="text-2xl font-bold text-green-500">-$25.05</p>
                <p className="text-sm text-muted-foreground">Credit to account</p>
                <Badge className="mt-2 bg-green-500/20 text-green-500">You're earning!</Badge>
              </div>
            </div>

            {/* Rate Information */}
            <div className="p-4 rounded-lg bg-muted/50">
              <h4 className="font-medium text-foreground mb-3">Current Rate Plan</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Peak Rate (4pm-9pm)</p>
                  <p className="font-medium text-foreground">$0.25/kWh</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Off-Peak Rate</p>
                  <p className="font-medium text-foreground">$0.12/kWh</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Feed-in Tariff</p>
                  <p className="font-medium text-foreground">$0.15/kWh</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Payment Info */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Payment
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
              <Leaf className="h-8 w-8 text-green-500 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No payment due</p>
              <p className="text-xl font-bold text-green-500">$25.05 Credit</p>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Account Balance</span>
                <span className="text-green-500 font-medium">-$25.05</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Next Bill Date</span>
                <span className="text-foreground">Dec 1, 2024</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Payment Method</span>
                <span className="text-foreground">Auto-pay</span>
              </div>
            </div>

            <Button className="w-full bg-transparent" variant="outline">
              Manage Payment <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Billing History */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Billing History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Period</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Import (kWh)</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Export (kWh)</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Cost</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Credit</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Net</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {billingHistory.map((bill, index) => (
                  <tr key={index} className="border-b border-border/50 hover:bg-muted/30">
                    <td className="py-3 px-4 text-sm text-foreground">{bill.month}</td>
                    <td className="py-3 px-4 text-sm text-right text-red-400">{bill.import}</td>
                    <td className="py-3 px-4 text-sm text-right text-green-500">{bill.export}</td>
                    <td className="py-3 px-4 text-sm text-right text-foreground">${bill.cost.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-right text-foreground">${bill.credit.toFixed(2)}</td>
                    <td
                      className={`py-3 px-4 text-sm text-right font-medium ${bill.net < 0 ? "text-green-500" : "text-red-400"}`}
                    >
                      {bill.net < 0 ? "-" : ""}${Math.abs(bill.net).toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button variant="ghost" size="sm">
                        <Download className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
