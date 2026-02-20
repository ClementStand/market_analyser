import { prisma } from '@/lib/prisma'
import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

async function getOrgId() {
    const supabase = createClient()
    const { data: { user }, error } = await supabase.auth.getUser()
    if (error || !user) return null

    const profile = await prisma.userProfile.findUnique({
        where: { email: user.email! }
    })
    return profile?.organizationId ?? null
}

// GET: Return org settings (vipCompetitors, priorityRegions, name, regions)
export async function GET() {
    try {
        const orgId = await getOrgId()
        if (!orgId) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        const org = await prisma.organization.findUnique({
            where: { id: orgId },
            select: {
                id: true,
                name: true,
                regions: true,
                vipCompetitors: true,
                priorityRegions: true,
                competitors: {
                    where: { status: 'active' },
                    select: { id: true, name: true },
                    orderBy: { name: 'asc' },
                },
            },
        })

        if (!org) {
            return NextResponse.json({ error: 'Organization not found' }, { status: 404 })
        }

        return NextResponse.json(org)
    } catch (error) {
        console.error('Settings GET error:', error)
        return NextResponse.json({ error: 'Failed to fetch settings' }, { status: 500 })
    }
}

// PATCH: Update vipCompetitors and/or priorityRegions
export async function PATCH(request: Request) {
    try {
        const orgId = await getOrgId()
        if (!orgId) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        const body = await request.json()
        const data: Record<string, any> = {}

        if (Array.isArray(body.vipCompetitors)) {
            data.vipCompetitors = body.vipCompetitors
        }
        if (Array.isArray(body.priorityRegions)) {
            data.priorityRegions = body.priorityRegions
        }

        if (Object.keys(data).length === 0) {
            return NextResponse.json({ error: 'No valid fields to update' }, { status: 400 })
        }

        const updated = await prisma.organization.update({
            where: { id: orgId },
            data,
            select: {
                vipCompetitors: true,
                priorityRegions: true,
            },
        })

        return NextResponse.json(updated)
    } catch (error) {
        console.error('Settings PATCH error:', error)
        return NextResponse.json({ error: 'Failed to update settings' }, { status: 500 })
    }
}
