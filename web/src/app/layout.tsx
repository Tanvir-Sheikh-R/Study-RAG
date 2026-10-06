import type { Metadata } from "next";
import { Hind_Siliguri } from "next/font/google";
import "./globals.css";

const bengali = Hind_Siliguri({
  subsets: ["bengali", "latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-bengali",
  display: "swap",
});

export const metadata: Metadata = {
  title: "বই বন্ধু",
  description: "পাঠ্যবই থেকে প্রশ্নের উত্তর — বাংলা স্টাডি অ্যাসিস্ট্যান্ট",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="bn" className={bengali.variable}>
      <body className="font-[family-name:var(--font-bengali)] antialiased">{children}</body>
    </html>
  );
}
