import { useEffect, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "../ui/drawer";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { NasaMetricCard } from "./NasaMetricCard";
import { alerts, severityBadgeClass } from "./data";
import { getAlerts } from "../../services/dashboardApi";

const trendData = [
  { day: "Mon", critical: 3, high: 5, medium: 7, low: 4 },
  { day: "Tue", critical: 2, high: 6, medium: 8, low: 5 },
  { day: "Wed", critical: 4, high: 7, medium: 6, low: 3 },
  { day: "Thu", critical: 5, high: 4, medium: 5, low: 6 },
  { day: "Fri", critical: 3, high: 5, medium: 7, low: 5 },
  { day: "Sat", critical: 2, high: 3, medium: 6, low: 4 },
  { day: "Sun", critical: 1, high: 4, medium: 5, low: 3 },
];

export function AlertsPage() {
  const [alertsFeed, setAlertsFeed] = useState(alerts);
  const [selectedAlertId, setSelectedAlertId] = useState(alerts[0].id);

  useEffect(() => {
    const load = async () => {
      try {
        const apiAlerts = await getAlerts();
        if (apiAlerts.length === 0) {
          return;
        }
        const mapped = apiAlerts.map((item) => ({
          id: item.id,
          engineId: item.engine_id,
          severity: (item.severity || "medium") as "critical" | "high" | "medium" | "low",
          score: 0.7,
          description: item.message,
          timestamp: item.created_at || "",
          status: "open" as const,
          rootCause: "Not available from alert payload.",
          recommendation: "Review telemetry history and investigate engine condition.",
        }));
        setAlertsFeed(mapped);
        setSelectedAlertId(mapped[0].id);
      } catch {
        setAlertsFeed(alerts);
      }
    };

    void load();
  }, []);

  const selected = alertsFeed.find((item) => item.id === selectedAlertId) ?? alertsFeed[0] ?? alerts[0];

  const summary = {
    critical: alertsFeed.filter((item) => item.severity === "critical").length,
    high: alertsFeed.filter((item) => item.severity === "high").length,
    medium: alertsFeed.filter((item) => item.severity === "medium").length,
    low: alertsFeed.filter((item) => item.severity === "low").length,
  };

  const pieData = [
    { name: "Critical", value: summary.critical, color: "#ef4444" },
    { name: "High", value: summary.high, color: "#f97316" },
    { name: "Medium", value: summary.medium, color: "#eab308" },
    { name: "Low", value: summary.low, color: "#3b82f6" },
  ];

  return (
    <div className="p-6 space-y-6 bg-background min-h-full">
      <div>
        <h1 className="text-3xl font-semibold text-foreground">Alerts</h1>
        <p className="text-muted-foreground mt-1">Alert triage, status workflow, and root-cause context.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <NasaMetricCard title="Critical" value={`${summary.critical}`} subtitle="Immediate intervention" />
        <NasaMetricCard title="High" value={`${summary.high}`} subtitle="Action this shift" />
        <NasaMetricCard title="Medium" value={`${summary.medium}`} subtitle="Monitor closely" />
        <NasaMetricCard title="Low" value={`${summary.low}`} subtitle="Track and review" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Alert Severity Distribution</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={70} outerRadius={105}>
                  {pieData.map((item) => <Cell key={item.name} fill={item.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Alert Trends Over Time</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line dataKey="critical" stroke="#ef4444" strokeWidth={2.2} />
                <Line dataKey="high" stroke="#f97316" strokeWidth={2.2} />
                <Line dataKey="medium" stroke="#eab308" strokeWidth={2.2} />
                <Line dataKey="low" stroke="#3b82f6" strokeWidth={2.2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
        <CardHeader>
          <CardTitle>Alert Table</CardTitle>
          <CardDescription>Engine ID, severity, score, description, timestamp, and status</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Engine ID</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alertsFeed.map((alert) => (
                <TableRow key={alert.id}>
                  <TableCell className="font-medium">{alert.engineId}</TableCell>
                  <TableCell>
                    <Badge className={severityBadgeClass(alert.severity)} variant="outline">{alert.severity.toUpperCase()}</Badge>
                  </TableCell>
                  <TableCell>{alert.score.toFixed(2)}</TableCell>
                  <TableCell>{alert.description}</TableCell>
                  <TableCell>{alert.timestamp}</TableCell>
                  <TableCell>{alert.status}</TableCell>
                  <TableCell>
                    <Drawer>
                      <DrawerTrigger asChild>
                        <Button size="sm" variant="outline" onClick={() => setSelectedAlertId(alert.id)}>View</Button>
                      </DrawerTrigger>
                      <DrawerContent>
                        <DrawerHeader>
                          <DrawerTitle>Alert Details: {selected.id}</DrawerTitle>
                          <DrawerDescription>{selected.engineId} | {selected.description}</DrawerDescription>
                        </DrawerHeader>
                        <div className="px-4 space-y-3">
                          <div className="p-3 rounded-lg bg-muted/50">
                            <p className="text-sm font-medium">Root Cause Analysis</p>
                            <p className="text-sm text-muted-foreground mt-1">{selected.rootCause}</p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/50">
                            <p className="text-sm font-medium">Recommended Actions</p>
                            <p className="text-sm text-muted-foreground mt-1">{selected.recommendation}</p>
                          </div>
                        </div>
                        <DrawerFooter>
                          <DrawerClose asChild>
                            <Button variant="outline">Close</Button>
                          </DrawerClose>
                        </DrawerFooter>
                      </DrawerContent>
                    </Drawer>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
