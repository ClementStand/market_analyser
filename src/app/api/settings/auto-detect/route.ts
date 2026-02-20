import { prisma } from '@/lib/prisma'
import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

// POST: Auto-detect VIP competitors based on news data
// Ranks competitors by: count of high-threat articles (threat >= 4) + total article count
export async function POST() {
    try {
        const supabase = createClient()
        const { data: { user }, error } = await supabase.auth.getUser()
        if (error || !user) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        const profile = await prisma.userProfile.findUnique({
            where: { email: user.email! }
        })
        if (!profile?.organizationId) {
            return NextResponse.json({ error: 'No organization found' }, { status: 400 })
        }

        const orgId = profile.organizationId

        // Get all active competitors with their news stats
        const competitors = await prisma.competitor.findMany({
            where: { organizationId: orgId, status: 'active' },
            select: {
                name: true,
                news: {
                    select: {
                        threatLevel: true,
                        impactScore: true,
                    },
                },
            },
        })

        // Score each competitor:
        // - Each high-threat article (threat >= 4) = 3 points
        // - Each high-impact article (impact >= 50) = 2 points
        // - Each regular article = 1 point
        const scored = competitors.map(c => {
            let score = 0
            for (const n of c.news) {
                if (n.threatLevel >= 4) score += 3
                else score += 1
                if (n.impactScore && n.impactScore >= 50) score += 2
            }
            return { name: c.name, score, articleCount: c.news.length }
        })

        // Sort by score descending, pick top 2 (or all if <= 2 competitors)
        scored.sort((a, b) => b.score - a.score)
        const vipNames = scored
            .filter(c => c.articleCount > 0)
            .slice(0, 2)
            .map(c => c.name)

        // Auto-detect priority regions: find regions with most high-threat news
        const allNews = await prisma.competitorNews.findMany({
            where: {
                competitor: { organizationId: orgId },
                threatLevel: { gte: 3 },
            },
            select: { region: true },
        })

        const regionCounts: Record<string, number> = {}
        for (const n of allNews) {
            if (n.region) {
                regionCounts[n.region] = (regionCounts[n.region] || 0) + 1
            }
        }

        const priorityRegions = Object.entries(regionCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 2)
            .map(([region]) => region)

        // Save to organization
        await prisma.organization.update({
            where: { id: orgId },
            data: { vipCompetitors: vipNames, priorityRegions },
        })

        return NextResponse.json({
            vipCompetitors: vipNames,
            priorityRegions,
            details: scored,
        })
    } catch (error: any) {
        console.error('Auto-detect error:', error)
        return NextResponse.json(
            { error: 'Failed to auto-detect', details: error.message },
            { status: 500 }
        )
    }
}
