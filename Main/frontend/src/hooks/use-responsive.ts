import { useState, useEffect } from "react";

export function useResponsive() {
  const [windowWidth, setWindowWidth] = useState<number>(1200); // Server default

  useEffect(() => {
    // Set initial width
    setWindowWidth(window.innerWidth);

    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  const isMobile = windowWidth < 768;
  const isTablet = windowWidth >= 768 && windowWidth < 1024;
  const isDesktop = windowWidth >= 1024;

  return {
    windowWidth,
    isMobile,
    isTablet,
    isDesktop,
  };
}
