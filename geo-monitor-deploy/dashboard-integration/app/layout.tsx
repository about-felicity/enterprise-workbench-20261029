import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "企业工作台",
  description: "企业统一工作台：GEO抓取分析、采集控制、产品知识库与内容创作",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
