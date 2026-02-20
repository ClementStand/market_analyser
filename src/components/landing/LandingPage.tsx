'use client'

import Navbar from './Navbar'
import Hero from './Hero'
import { ProductShowcase } from './ProductShowcase'
import PoweredBy from './PoweredBy'
import ProofSection from './ProofSection'
import FeaturesGrid from './FeaturesGrid'
import SignalVsNoise from './SignalVsNoise'
import FounderProfile from './FounderProfile'
import Footer from './Footer'

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased">
            <Navbar />
            <Hero />
            <PoweredBy />
            <ProductShowcase />
            <FeaturesGrid />
            <SignalVsNoise />
            <ProofSection />
            <FounderProfile />
            <Footer />
        </div>
    )
}
