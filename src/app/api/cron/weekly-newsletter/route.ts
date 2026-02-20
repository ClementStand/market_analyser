import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { sendWeeklyNewsletter } from '@/lib/email'

export async function POST(request: Request) {
    // Authenticate with CRON_SECRET
    const authHeader = request.headers.get('authorization')
    const cronSecret = process.env.CRON_SECRET

    if (!cronSecret) {
        return NextResponse.json(
            { error: 'CRON_SECRET not configured' },
            { status: 500 }
        )
    }

    if (authHeader !== `Bearer ${cronSecret}`) {
        return NextResponse.json(
            { error: 'Unauthorized' },
            { status: 401 }
        )
    }

    const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    const dashboardBaseUrl = process.env.APP_URL || 'https://market-analyser-dtcf.vercel.app'

    try {
        const organizations = await prisma.organization.findMany({
            include: {
                users: { select: { email: true } },
            },
        })

        let sentCount = 0

        for (const org of organizations) {
            if (org.users.length === 0) continue

            // Query top 3 articles by impactScore (fallback to threatLevel)
            const topArticles = await prisma.competitorNews.findMany({
                where: {
                    date: { gte: sevenDaysAgo },
                    competitor: { organizationId: org.id },
                },
                orderBy: [
                    { impactScore: 'desc' },
                    { threatLevel: 'desc' },
                    { date: 'desc' },
                ],
                take: 3,
                include: { competitor: true },
            })

            const articles = topArticles.map((a) => ({
                title: a.title,
                competitorName: a.competitor.name,
                impactScore: a.impactScore,
                eventType: a.eventType,
            }))

            for (const user of org.users) {
                try {
                    await sendWeeklyNewsletter(
                        user.email,
                        org.name,
                        articles,
                        dashboardBaseUrl
                    )
                    sentCount++
                } catch (err) {
                    console.error(`Newsletter failed for ${user.email}:`, err)
                }
            }
        }

        return NextResponse.json({
            message: 'Weekly newsletters sent',
            sentCount,
            orgCount: organizations.length,
        })
    } catch (error: any) {
        console.error('Weekly newsletter cron error:', error)
        return NextResponse.json(
            { error: 'Failed to send newsletters', details: error.message },
            { status: 500 }
        )
    }
}
