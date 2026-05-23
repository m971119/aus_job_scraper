import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aus Job Scraper",
  description: "Seek job listings scraper",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
