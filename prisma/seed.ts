import fs from 'fs'
import path from 'path'
import { parse } from 'csv-parse/sync'
import { prisma } from '../src/lib/prisma'

interface CSVRecord {
    Company: string
    Category: string
    Website: string
    'Key Markets': string
    'HQ Location': string
    'Primary Solution': string
}

async function main() {
    console.log('🌱 Seeding competitors from CSV...')

    // Clear existing data
    await prisma.competitorNews.deleteMany({})
    await prisma.competitor.deleteMany({})

    // Read CSV
    const csvPath = path.join(process.cwd(), 'competitors2.csv')
    const fileContent = fs.readFileSync(csvPath, 'utf8')

    // Use loose typed CSV parse
    const rawRecords = parse(fileContent, {
        columns: true,
        skip_empty_lines: true
    }) as any[]

    console.log(`📋 Found ${rawRecords.length} records in CSV.`)

    // Filter and validate
    const competitors: any[] = []

    for (const r of rawRecords) {
        const name = r.Company?.trim()

        // Skip invalid rows (no company name)
        if (!name) continue

        // Skip Abuzz (our company)
        if (name.toLowerCase().includes('abuzz')) continue

        competitors.push(r)
    }

    console.log(`🏢 Loading ${competitors.length} competitors...`)

    for (const record of competitors) {
        const name = record.Company.trim()
        const websiteUrl = record.Website?.trim() || null
        const category = record.Category?.trim() || null
        const keyMarkets = record['Key Markets']?.trim() || null
        const hqLocation = record['HQ Location']?.trim() || null
        const primarySolution = record['Primary Solution']?.trim() || null
        const employees = record['Approx Employees']?.trim() || null
        const revenue = record['Est. Revenue (USD)']?.trim() || null
        const fundingStatus = record['Funding/Status']?.trim() || null

        await prisma.competitor.create({
            data: {
                name: name,
                website: websiteUrl,
                description: primarySolution,
                industry: category,
                region: keyMarkets || hqLocation,
                headquarters: hqLocation,
                employeeCount: employees,
                revenue: revenue,
                fundingStatus: fundingStatus,
                keyMarkets: keyMarkets,
                status: 'active'
            }
        })

        console.log(`  ✓ ${name}`)
    }

    const count = await prisma.competitor.count()
    console.log(`\n✅ Seeding complete! ${count} competitors loaded.`)
    console.log(`\n📰 Run this to fetch real news:`)
    console.log(`   python scripts/news_fetcher.py --test`)
}

main()
    .then(async () => {
        await prisma.$disconnect()
    })
    .catch(async (e) => {
        console.error(e)
        await prisma.$disconnect()
        process.exit(1)
    })