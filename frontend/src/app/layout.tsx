import type { Metadata } from "next";
import { Cairo } from "next/font/google";
import "./globals.css";

// Cairo font, exposed as a CSS variable used by Tailwind's font-sans.
const cairo = Cairo({
  subsets: ["arabic", "latin"],
  variable: "--font-cairo",
  display: "swap",
});

export const metadata: Metadata = {
  title: "نظام رواتب موظفي الدولة العراقية",
  description: "نظام احتساب رواتب موظفي الدولة — العرض وإدخال البيانات فقط",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl" className={cairo.variable}>
      <body>{children}</body>
    </html>
  );
}
