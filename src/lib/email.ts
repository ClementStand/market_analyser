import { Resend } from 'resend'

function getResend() {
    if (!process.env.RESEND_API_KEY) {
        throw new Error('RESEND_API_KEY is not configured')
    }
    return new Resend(process.env.RESEND_API_KEY)
}

export async function sendAnalysisCompleteEmail(to: string, orgName: string, dashboardUrl: string) {
    const resend = getResend()
    const { error } = await resend.emails.send({
        from: 'Market Analyser <onboarding@resend.dev>',
        to,
        subject: `Analysis Complete - ${orgName}`,
        html: `
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 500px; margin: 0 auto; padding: 32px;">
                <h2 style="color: #0f172a; margin-bottom: 16px;">Analysis Complete</h2>
                <p style="color: #475569; line-height: 1.6;">
                    Your competitor intelligence analysis for <strong>${orgName}</strong> has finished.
                    New articles have been added to your dashboard.
                </p>
                <a href="${dashboardUrl}" style="display: inline-block; margin-top: 20px; padding: 12px 24px; background-color: #0891b2; color: white; text-decoration: none; border-radius: 8px; font-weight: 500;">
                    View Dashboard
                </a>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 32px;">
                    Market Analyser - Competitor Intelligence Platform
                </p>
            </div>
        `,
    })

    if (error) {
        console.error('Failed to send email:', error)
        throw error
    }
}
