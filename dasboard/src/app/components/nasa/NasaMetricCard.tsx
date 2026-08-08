import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

interface NasaMetricCardProps {
  title: string;
  value: string;
  subtitle: string;
}

export function NasaMetricCard({ title, value, subtitle }: NasaMetricCardProps) {
  return (
    <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold text-foreground">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      </CardContent>
    </Card>
  );
}
