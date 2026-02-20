import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

export async function GET(request: Request) {
    const { searchParams, origin } = new URL(request.url)
    const token_hash = searchParams.get('token_hash')
    const type = searchParams.get('type') as 'email' | 'signup' | 'email_change' | null
    const next = searchParams.get('next') ?? '/onboarding'

    console.log(`[Auth Confirm] token_hash: ${token_hash ? 'present' : 'missing'}, type: ${type}, next: ${next}`)

    if (token_hash && type) {
        const supabase = createClient()
        const { error } = await supabase.auth.verifyOtp({
            token_hash,
            type,
        })

        if (!error) {
            console.log(`[Auth Confirm] Verification successful, redirecting to ${next}`)
            return NextResponse.redirect(`${origin}${next}`)
        }

        console.error(`[Auth Confirm] Verification failed: ${error.message}`)
    }

    // If verification fails, redirect to error page
    return NextResponse.redirect(`${origin}/auth/auth-code-error`)
}
