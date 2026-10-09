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
    // suppressHydrationWarning covers third-party attributes injected into <html>
    // before hydration (dark-mode and reading extensions such as Night Eye add
    // e.g. nighteye="disabled"), which React otherwise reports as a mismatch.
    // It only applies to this element's own attributes, not to the tree below it.
    <html lang="bn" className={bengali.variable} suppressHydrationWarning>
      <body className="font-[family-name:var(--font-bengali)] antialiased">{children}</body>
    </html>
  );
}
