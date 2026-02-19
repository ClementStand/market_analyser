
import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'
import { prisma } from '@/lib/prisma'

export async function GET(request: Request) {
    const { searchParams, origin } = new URL(request.url)
    const code = searchParams.get('code')
    // if "next" is in param, use it as the redirect URL
    const next = searchParams.get('next') ?? '/'

    if (code) {
        const supabase = createClient()
        const { error } = await supabase.auth.exchangeCodeForSession(code)
        if (!error) {
            // Check if user has completed onboarding (has a profile with an org)
            const { data: { user } } = await supabase.auth.getUser()
            if (user?.email) {
                const profile = await prisma.userProfile.findUnique({
                    where: { email: user.email }
                })
                if (!profile?.organizationId) {
                    return NextResponse.redirect(`${origin}/onboarding`)
                }
            }
            return NextResponse.redirect(`${origin}${next}`)
        }
    }

    // return the user to an error page with instructions
    return NextResponse.redirect(`${origin}/auth/auth-code-error`)
}
