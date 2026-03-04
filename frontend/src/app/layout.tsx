import type { Metadata } from "next";
import localFont from "next/font/local";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

const barlowCondensed = localFont({
  variable: "--font-display",
  src: [
    { path: "./fonts/barlow-condensed-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/barlow-condensed-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/barlow-condensed-600.woff2", weight: "600", style: "normal" },
    { path: "./fonts/barlow-condensed-700.woff2", weight: "700", style: "normal" },
  ],
  display: "swap",
});

const barlow = localFont({
  variable: "--font-body",
  src: [
    { path: "./fonts/barlow-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/barlow-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/barlow-600.woff2", weight: "600", style: "normal" },
  ],
  display: "swap",
});

const ibmPlexMono = localFont({
  variable: "--font-mono",
  src: [
    { path: "./fonts/ibm-plex-mono-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/ibm-plex-mono-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/ibm-plex-mono-600.woff2", weight: "600", style: "normal" },
  ],
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
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        suppressHydrationWarning
        className={`${barlowCondensed.variable} ${barlow.variable} ${ibmPlexMono.variable} antialiased`}
      >
        <AuthProvider>
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
        </AuthProvider>
      </body>
    </html>
  );
}
