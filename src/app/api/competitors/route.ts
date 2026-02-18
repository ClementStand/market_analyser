import { prisma } from '@/lib/prisma'
import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

export async function GET() {
    try {
        const supabase = createClient()
        const { data: { user }, error } = await supabase.auth.getUser()

        if (error || !user) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        // Get user's org
        const userProfile = await prisma.userProfile.findUnique({
            where: { email: user.email! }
        })

        if (!userProfile) {
            return NextResponse.json({ error: 'User profile not found' }, { status: 404 })
        }

        const competitors = await prisma.competitor.findMany({
            where: {
                status: 'active',
                organizationId: userProfile.organizationId
            },
            include: {
                _count: {
                    select: { news: true }
                }
            },
            orderBy: { name: 'asc' }
        })

        const formatted = competitors.map(c => ({
            ...c,
            newsCount: c._count.news
        }))

        return NextResponse.json(formatted)
    } catch (error) {
        console.error(error)
        return NextResponse.json({ error: 'Failed to fetch competitors' }, { status: 500 })
    }
}

export async function POST(request: Request) {
    try {
        const supabase = createClient()
        const { data: { user }, error } = await supabase.auth.getUser()

        if (error || !user) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        const userProfile = await prisma.userProfile.findUnique({
            where: { email: user.email! }
        })

        if (!userProfile) {
            return NextResponse.json({ error: 'User profile not found' }, { status: 404 })
        }

        const { name, website, region } = await request.json()

        // Enforce 5-competitor limit
        const activeCount = await prisma.competitor.count({
            where: {
                organizationId: userProfile.organizationId,
                status: 'active'
            }
        })

        if (activeCount >= 5) {
            return NextResponse.json(
                { error: 'Maximum of 5 active competitors allowed. Archive a competitor to add a new one.' },
                { status: 400 }
            )
        }

        const competitor = await prisma.competitor.create({
            data: {
                name,
                website,
                region,
                status: 'active',
                organizationId: userProfile.organizationId
            }
        })
        return NextResponse.json(competitor)
    } catch (error) {
        console.error(error)
        return NextResponse.json({ error: 'Failed to create competitor' }, { status: 500 })
    }
}

export async function PATCH(request: Request) {
    try {
        const { id, status } = await request.json()
        const competitor = await prisma.competitor.update({
            where: { id },
            data: { status }
        })
        return NextResponse.json(competitor)
    } catch (error) {
        console.error(error)
        return NextResponse.json({ error: 'Failed to update competitor' }, { status: 500 })
    }
}
