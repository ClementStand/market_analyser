import React from 'react';
// Using actual SVG paths for the requested logos
const PARTNERS = [
    {
        name: 'Anthropic',
        svg: <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M17.443 2.053h-3.924l-9.172 19.89h3.707l1.793-4.103h9.613l1.782 4.103h3.76zM11.516 14.5l3.414-7.85 3.424 7.85z" /></svg>
    },
    {
        name: 'Google Gemini',
        svg: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-slate-300"><path d="M11.9546 23.9092C11.9546 17.3117 6.5975 11.9546 0 11.9546C6.5975 11.9546 11.9546 6.5975 11.9546 0C11.9546 6.5975 17.3117 11.9546 23.9092 11.9546C17.3117 11.9546 11.9546 17.3117 11.9546 23.9092Z" fill="currentColor" /></svg>
    },
    {
        name: 'Supabase',
        svg: <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M21.362 9.354H12V.396a.396.396 0 0 0-.712-.238L2.096 11.986A.396.396 0 0 0 2.41 12.6h9.362v8.958a.396.396 0 0 0 .712.238l9.192-11.828a.396.396 0 0 0-.314-.614z" /></svg>
    },
    {
        name: 'Vercel',
        svg: <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M24 22.525H0l12-21.05 12 21.05z" /></svg>
    },
    {
        name: 'Railway',
        svg: <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M24 10.125a1.875 1.875 0 10-3.75 0 1.875 1.875 0 003.75 0zm-14.25-1.5a1.875 1.875 0 100-3.75 1.875 1.875 0 000 3.75zm10.5 8.25a1.875 1.875 0 10-3.75 0 1.875 1.875 0 003.75 0zm-15-5.25a1.875 1.875 0 100-3.75 1.875 1.875 0 000 3.75zm7.5-6.75a1.875 1.875 0 100-3.75 1.875 1.875 0 000 3.75zm0 13.5a1.875 1.875 0 100-3.75 1.875 1.875 0 000 3.75z" /></svg>
    },
    {
        name: 'Serper.dev',
        svg: <svg role="img" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 0 0 1.48-5.34c-.47-2.78-2.79-5-5.59-5.34a6.505 6.505 0 0 0-7.27 7.27c.34 2.8 2.56 5.12 5.34 5.59a6.5 6.5 0 0 0 5.34-1.48l.27.28v.79l4.25 4.25c.41.41 1.08.41 1.49 0 .41-.41.41-1.08 0-1.49L15.5 14zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" /></svg>
    }
];

export default function PoweredBy() {
    return (
        <section className="py-16 bg-slate-950 relative overflow-hidden border-y border-slate-900/50">
            <div className="max-w-7xl mx-auto px-4 md:px-8">
                <h2 className="text-center text-xs font-semibold text-slate-500 tracking-[0.25em] mb-10 w-full">
                    POWERED BY ENTERPRISE-GRADE AI & INFRASTRUCTURE
                </h2>

                {/* Marquee Wrapper with CSS Mask for edge fading */}
                <div
                    className="relative flex overflow-hidden group"
                    style={{
                        maskImage: 'linear-gradient(to right, transparent, black 15%, black 85%, transparent)',
                        WebkitMaskImage: 'linear-gradient(to right, transparent, black 15%, black 85%, transparent)'
                    }}
                >
                    {/* Marquee Track Container */}
                    <div className="flex w-max animate-marquee hover:[animation-play-state:paused] items-center" style={{ animationDuration: '20s' }}>

                        {/* Set 1 */}
                        <div className="flex gap-16 md:gap-24 pr-16 md:pr-24 min-w-full justify-around items-center">
                            {PARTNERS.map((partner, idx) => (
                                <div
                                    key={`set1-${partner.name}-${idx}`}
                                    className="flex items-center gap-3 grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all duration-300 w-max cursor-default"
                                >
                                    <div className="w-8 h-8 text-slate-300 flex items-center justify-center">
                                        {partner.svg}
                                    </div>
                                    <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-slate-200 to-slate-400">
                                        {partner.name}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Set 2 (Duplicate for seamless loop) */}
                        <div aria-hidden="true" className="flex gap-16 md:gap-24 pr-16 md:pr-24 min-w-full justify-around items-center">
                            {PARTNERS.map((partner, idx) => (
                                <div
                                    key={`set2-${partner.name}-${idx}`}
                                    className="flex items-center gap-3 grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all duration-300 w-max cursor-default"
                                >
                                    <div className="w-8 h-8 text-slate-300 flex items-center justify-center">
                                        {partner.svg}
                                    </div>
                                    <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-slate-200 to-slate-400">
                                        {partner.name}
                                    </span>
                                </div>
                            ))}
                        </div>

                    </div>
                </div>
            </div>
        </section>
    );
}
