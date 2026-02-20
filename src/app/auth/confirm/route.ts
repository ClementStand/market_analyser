import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

export async function GET(request: Request) {
    const { searchParams, origin } = new URL(request.url)
    const token_hash = searchParams.get('token_hash')
    const type = searchParams.get('type') as 'email' | 'signup' | null
    const next = searchParams.get('next') ?? '/onboarding'

    if (token_hash && type) {
        const supabase = createClient()
        const { error } = await supabase.auth.verifyOtp({
            token_hash,
            type,
        })

        if (!error) {
            return NextResponse.redirect(`${origin}${next}`)
        }
    }

    // If verification fails, redirect to error page
    return NextResponse.redirect(`${origin}/auth/auth-code-error`)
}
