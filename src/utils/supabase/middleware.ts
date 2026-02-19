import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function updateSession(request: NextRequest) {
    let response = NextResponse.next({
        request: {
            headers: request.headers,
        },
    });

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll();
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value, options }) => {
                        request.cookies.set(name, value);
                    });
                    response = NextResponse.next({
                        request,
                    });
                    cookiesToSet.forEach(({ name, value, options }) => {
                        response.cookies.set(name, value, options);
                    });
                },
            },
        },
    );

    // refreshing the auth token
    const { data: { user }, error } = await supabase.auth.getUser();
    if (error) {
        console.log(`[Middleware] getUser error: ${error.message} (${error.status})`)
    }

    // Protect routes
    if (!user && !request.nextUrl.pathname.startsWith('/login') && !request.nextUrl.pathname.startsWith('/signup') && !request.nextUrl.pathname.startsWith('/auth')) {
        console.log(`[Middleware] Unauthorized access to: ${request.nextUrl.pathname}`)
        // API routes: Return 401 JSON
        if (request.nextUrl.pathname.startsWith('/api/')) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }

        // Pages: Redirect to Login
        const url = request.nextUrl.clone()
        url.pathname = '/login'
        return NextResponse.redirect(url)
    }

    // If user is logged in but hasn't completed onboarding, redirect to /onboarding
    if (user && !request.nextUrl.pathname.startsWith('/onboarding') && !request.nextUrl.pathname.startsWith('/auth') && !request.nextUrl.pathname.startsWith('/api/')) {
        try {
            const profile = await prisma.userProfile.findUnique({
                where: { email: user.email! }
            })
            if (!profile?.organizationId) {
                const url = request.nextUrl.clone()
                url.pathname = '/onboarding'
                return NextResponse.redirect(url)
            }
        } catch (e) {
            // If DB check fails, let the request through — the page itself will handle it
        }
    }

    return response;
}
