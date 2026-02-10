import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function POST(req: Request) {
    try {
        const body = await req.json()
        const { mode, startDate, endDate } = body

        // Count mode: return count of news items in range
        if (mode === 'count') {
            const where: any = {}
            if (startDate && endDate) {
                where.date = {
                    gte: new Date(startDate),
                    lte: new Date(endDate),
                }
            }
            const count = await prisma.competitorNews.count({ where })
            return NextResponse.json({ count })
        }

        // Latest mode: return the most recent debrief from DB
        const latest = await prisma.debrief.findFirst({
            orderBy: { generatedAt: 'desc' },
        })

        if (!latest) {
            return NextResponse.json({
                response: null,
                message: 'No debrief generated yet. Run the generator script locally.',
            })
        }

        return NextResponse.json({
            response: latest.content,
            itemCount: latest.itemCount,
            generatedAt: latest.generatedAt,
            periodStart: latest.periodStart,
            periodEnd: latest.periodEnd,
        })
    } catch (error: any) {
        console.error('Debrief error:', error)
        return NextResponse.json(
            { error: 'Failed to fetch debrief', details: error.message },
            { status: 500 }
        )
    }
}
