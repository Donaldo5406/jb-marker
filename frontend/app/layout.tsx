import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JB Marker",
  description: "금융 마케팅을 쉽게",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
