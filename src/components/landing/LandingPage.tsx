'use client'

import Navbar from './Navbar'
import Hero from './Hero'
import { ProductShowcase } from './ProductShowcase'
import ProofSection from './ProofSection'
import FeaturesGrid from './FeaturesGrid'
import FounderSection from './FounderSection'
import Footer from './Footer'

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased">
            <Navbar />
            <Hero />
            <ProductShowcase />
            <FeaturesGrid />
            <ProofSection />
            <FounderSection />
            <Footer />
        </div>
    )
}
