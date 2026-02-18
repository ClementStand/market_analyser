import { NextResponse } from 'next/server'
import { Prisma } from '@prisma/client'
import { prisma } from '@/lib/prisma'
import { createClient } from '@/utils/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
    try {
        // Get user's org
        const supabase = createClient()
        const { data: { user } } = await supabase.auth.getUser()

        if (!user) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        const profile = await prisma.userProfile.findUnique({
            where: { email: user.email! }
        })

        if (!profile?.organizationId) {
            return NextResponse.json({ error: 'No organization found' }, { status: 400 })
        }

        const { searchParams } = new URL(request.url)

        // Get filter params
        const competitorId = searchParams.get('competitor') || undefined
        const eventType = searchParams.get('eventType') || undefined
        const minThreat = searchParams.get('minThreat')
        const unreadOnly = searchParams.get('unread') === 'true'
        const starredOnly = searchParams.get('starred') === 'true'

        // Build where clause — scoped to user's org
        const where: Prisma.CompetitorNewsWhereInput = {
            AND: [
                {
                    sourceUrl: {
                        not: {
                            contains: 'example.com'
                        }
                    }
                },
                {
                    competitor: {
                        status: 'active',
                        organizationId: profile.organizationId
                    }
                }
            ]
        }

        if (competitorId) {
            where.competitorId = competitorId
        }

        if (eventType) {
            where.eventType = eventType
        }

        if (minThreat && !isNaN(parseInt(minThreat))) {
            where.threatLevel = {
                gte: parseInt(minThreat)
            }
        }

        if (unreadOnly) {
            where.isRead = false
        }

        if (starredOnly) {
            where.isStarred = true
        }

        const news = await prisma.competitorNews.findMany({
            where,
            include: {
                competitor: {
                    select: {
                        id: true,
                        name: true,
                        website: true
                    }
                }
            },
            orderBy: {
                date: 'desc'
            },
            take: 100
        })

        return NextResponse.json({ news })

    } catch (error) {
        console.error('Error fetching news:', error)
        return NextResponse.json(
            { error: 'Failed to fetch news' },
            { status: 500 }
        )
    }
}
