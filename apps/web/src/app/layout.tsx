import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KalshiBot Dashboard",
  description: "Personal Kalshi World Cup trading bot dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
