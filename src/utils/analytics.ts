export const initGoogleAnalytics = () => {
  if (import.meta.env.VITE_GA_TRACKING_ID) {
    const script = document.createElement("script");
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${import.meta.env.VITE_GA_TRACKING_ID}`;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    function gtag(...args: any[]) {
      (window.dataLayer as any).push(args);
    }

    gtag("js", new Date());
    gtag("config", import.meta.env.VITE_GA_TRACKING_ID);
  }
};

export const trackEvent = (action: string, category: string, label: string, value?: number) => {
  if (window.gtag) {
    window.gtag("event", action, { event_category: category, event_label: label, value });
  }
};