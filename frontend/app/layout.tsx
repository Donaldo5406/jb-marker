import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SentryInit } from "@/components/SentryInit";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "JB Marker",
  description: "금융 마케팅을 쉽게",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={inter.variable}>
      <body>
        <SentryInit />
        {children}
      </body>
    </html>
  );
}
