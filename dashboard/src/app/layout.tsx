import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QC Dashboard – Calcium Imaging Pipeline",
  description: "Real-time quality control for multi-lab calcium imaging",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white antialiased">{children}</body>
    </html>
  );
}
