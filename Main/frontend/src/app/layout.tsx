"use client";

import React from "react";
import "./globals.css";
import { AnalysisProvider } from "../stores/analysis-store";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <title>TalentAlign — Resume & JD Intelligence Platform</title>
        <meta 
          name="description" 
          content="SaaS-style resume alignment dashboard leveraging multi-source parsing and semantic match confidence scoring." 
        />
        {/* Load Inter Font */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link 
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className="antialiased min-h-screen text-foreground bg-background font-sans">
        <AnalysisProvider>
          {children}
        </AnalysisProvider>
      </body>
    </html>
  );
}
