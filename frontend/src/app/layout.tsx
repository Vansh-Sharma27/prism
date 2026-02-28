import type { Metadata } from "next";
import { Barlow_Condensed, Barlow, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const barlowCondensed = Barlow_Condensed({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const barlow = Barlow({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "PRISM | Parking Control System",
  description:
    "Industrial parking slot monitoring and control system powered by IoT sensors",
  keywords: ["parking", "IoT", "control system", "monitoring", "industrial"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${barlowCondensed.variable} ${barlow.variable} ${ibmPlexMono.variable} antialiased`}
      >
        {/* Skip link for keyboard navigation */}
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>

        {/* Live region for screen reader announcements */}
        <div
          id="live-region"
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        />

        {children}
      </body>
    </html>
  );
}
