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

interface NewsletterArticle {
    title: string
    competitorName: string
    impactScore: number | null
    eventType: string
}

export async function sendWeeklyNewsletter(
    to: string,
    orgName: string,
    articles: NewsletterArticle[],
    dashboardUrl: string
) {
    const resend = getResend()

    const articleListHtml = articles
        .map(
            (a) =>
                `<li style="margin-bottom: 16px;">
                    <strong style="color: #f1f5f9; font-size: 14px;">${a.title}</strong>
                    <br/>
                    <span style="color: #94a3b8; font-size: 12px;">
                        ${a.competitorName} &middot; ${a.eventType}${a.impactScore ? ` &middot; Impact: ${a.impactScore}/100` : ''}
                    </span>
                </li>`
        )
        .join('')

    const html = `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px; background-color: #0f172a; border-radius: 12px;">
            <h2 style="color: #f1f5f9; margin-bottom: 8px;">Weekly Intelligence Brief</h2>
            <p style="color: #64748b; font-size: 13px; margin-bottom: 24px;">${orgName} &mdash; Top stories this week</p>

            ${articles.length > 0
                ? `<ul style="list-style: none; padding: 0; margin: 0 0 24px 0;">${articleListHtml}</ul>`
                : '<p style="color: #94a3b8;">No significant competitor activity this week.</p>'
            }

            <a href="${dashboardUrl}" style="display: inline-block; padding: 12px 24px; background-color: #0891b2; color: white; text-decoration: none; border-radius: 8px; font-weight: 500; font-size: 14px;">
                View Deep Dive on Scoper
            </a>

            <p style="color: #475569; font-size: 11px; margin-top: 32px;">
                Scoper &mdash; Competitive Intelligence Platform
            </p>
        </div>
    `

    const { error } = await resend.emails.send({
        from: 'Scoper <onboarding@resend.dev>',
        to,
        subject: `Weekly Intel Brief - ${orgName}`,
        html,
    })

    if (error) {
        console.error('Failed to send newsletter:', error)
        throw error
    }
}
