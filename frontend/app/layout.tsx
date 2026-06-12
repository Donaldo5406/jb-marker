import type { Metadata } from "next";
import "./globals.css";
import { SentryInit } from "@/components/SentryInit";

export const metadata: Metadata = {
  title: "JB Marker",
  description: "금융 마케팅을 쉽게",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <SentryInit />
        {children}
      </body>
    </html>
  );
}
