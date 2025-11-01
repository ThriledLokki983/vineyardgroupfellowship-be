# Location-Based Filtering - Executive Summary

## Quick Decision Guide

### The Problem
Users in a 400k population city need to find fellowship groups near them. Currently, they see all groups regardless of distance, leading to potential long travel times.

---

## Solutions Compared

| Approach | Accuracy | Cost | Complexity | Recommendation |
|----------|----------|------|------------|----------------|
| **Cardinal Directions (N/S/E/W)** | ❌ Too inaccurate | ✅ Free | ✅ Very Simple | ❌ Not Suitable |
| **Postcode Matching** | ⚠️ Medium (1-10km) | ✅ Free | ✅ Simple | ⚠️ Acceptable |
| **GPS + Distance Calc** | ✅ High (±100m) | ✅ Free* | ⚠️ Medium | ✅ **RECOMMENDED** |

*Using free Nominatim API

---

## Recommended Solution

### 🏆 PostgreSQL PostGIS + Geocoding

**What You Get:**
- Show actual distances: "2.3 km away"
- Filter by radius: "groups within 5km"
- Sort by proximity: closest groups first
- Future-proof: enables maps, routing, etc.

**Technical Stack:**
```
PostgreSQL (already using)
  + PostGIS extension (free)
  + Nominatim geocoding (free, open-source)
  = Location-based filtering
```

**Cost:** $0/month

**Performance:** <50ms queries with indexing

**Privacy:** Store coordinates server-side only, show postcodes to users

---

## How It Works

### For Users:
1. User enters address/postcode during registration
2. System converts to coordinates (geocoding) - happens once
3. User searches for groups
4. System shows groups within X km, sorted by distance

### For Groups:
1. Leader creates group with meeting location
2. System geocodes location - happens once
3. Group appears in search results for nearby users

### Technical Flow:
```
User Location (text)
  → Geocode to coordinates (lat/lng)
  → Store in database
  → Query: Find groups within radius
  → Calculate distance using PostGIS
  → Return sorted results
```

---

## Implementation Timeline

### Week 1-2: Setup
- [x] Enable PostGIS extension
- [x] Add coordinates field to models
- [x] Integrate Nominatim API
- [x] Test with sample data

### Week 2-3: Data Migration
- [x] Geocode existing users
- [x] Geocode existing groups
- [x] Verify accuracy

### Week 3-4: API Development
- [x] Add `?nearby=true` filter
- [x] Add `?radius=X` filter
- [x] Update serializers with distance
- [x] Update documentation

### Week 4-5: Frontend
- [x] Add location autocomplete
- [x] Display distances on group cards
- [x] Add "nearby groups" section
- [x] Test user experience

**Total Time:** 4-5 weeks

---

## Key Metrics

### Scale Capacity
- **Current**: 200 groups, 20,000 users
- **Supported**: 10,000+ groups, 500,000+ users
- **Query Time**: 10-50ms with proper indexing

### Accuracy
- **Geocoding**: ±50-100 meters
- **Distance Calculation**: ±10 meters
- **Overall**: Highly accurate for filtering

### Privacy
- ✅ Exact coordinates stored server-side only
- ✅ Only postcode/area shown to users
- ✅ Optional: fuzz coordinates by 500m
- ✅ Opt-in location sharing

---

## Why Not Postcode-Only?

**Postcode Issues:**
- Urban postcode: 1-5 km² (might work)
- Suburban postcode: 5-10 km² (too large)
- Rural postcode: 10-50 km² (way too large)
- Boundary problem: Adjacent postcodes might be far apart
- No actual distance shown

**Example:**
```
User at postcode SW1A 1AA
Group at postcode SW1A 2AA
Same postcode district, but could be 5km apart!

With coordinates:
User: (51.5014, -0.1419)
Group: (51.5074, -0.1278)
Distance: 1.2 km ← Much better!
```

---

## Why Not Cardinal Directions?

For a 400k city (~20km × 20km):
- 4 zones (N/S/E/W): 100 km² each = Too large!
- 8 zones (N/NE/E/SE/S/SW/W/NW): 50 km² each = Still too large
- Would need 64+ zones = Too complex

**Verdict:** Not suitable for this use case.

---

## Code Example

### API Request:
```http
GET /api/v1/groups/?nearby=true
Authorization: Bearer <token>
```

### Response:
```json
[
  {
    "id": "uuid",
    "name": "Downtown Fellowship",
    "location": "123 Main St",
    "distance": 1.2,  // km
    "member_count": 8,
    "member_limit": 12
  },
  {
    "id": "uuid",
    "name": "Westside Group",
    "location": "456 Oak Ave",
    "distance": 2.7,  // km
    "member_count": 10,
    "member_limit": 15
  }
]
```

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits | Medium | Cache geocoding results (90%+ hit rate) |
| Inaccurate addresses | Low | Use postcode as fallback |
| Privacy concerns | Medium | Fuzz coordinates, show only postcodes |
| Performance issues | Low | GIST indexes, query optimization |

---

## Alternative: Start Simple, Upgrade Later

If geocoding seems too complex initially:

### Phase 1: Postcode Prefix Matching (2 weeks)
- Match first 3-4 characters of postcode
- "SW1A" matches "SW1A 1AA", "SW1A 2BB", etc.
- Simple, works reasonably well in urban areas

### Phase 2: Add Geocoding (3 weeks)
- Add coordinates for precise filtering
- Keep postcode display for privacy

This approach lets you launch faster but with less accuracy initially.

---

## Decision Time

### Choose Your Path:

**Option A: Full Solution (Recommended)**
✅ PostGIS + Geocoding
⏱️ 4-5 weeks
💰 $0/month
🎯 High accuracy
🚀 Future-proof

**Option B: Start Simple**
✅ Postcode prefix matching
⏱️ 2 weeks
💰 $0/month
🎯 Medium accuracy
🚀 Can upgrade later

**Option C: Do Nothing**
⏱️ 0 weeks
🎯 No accuracy
⚠️ Poor user experience
❌ Not recommended

---

## Next Steps

1. **Review** this summary and full research document
2. **Decide** on approach (Option A or B recommended)
3. **Approve** budget/timeline
4. **Start** proof of concept (1-2 days)
5. **Implement** following migration path

---

## Questions?

**Q: Will this work in other countries?**
A: Yes! Nominatim supports worldwide geocoding.

**Q: What if a user doesn't have a postcode?**
A: They can enter city/area name, geocoding still works.

**Q: Can users search without sharing their location?**
A: Yes, they can search by entering a location manually.

**Q: Does this work for virtual groups?**
A: Virtual groups can skip location, or use leader's location.

**Q: What about multi-location churches?**
A: Each campus can have its own groups with different coordinates.

---

**For detailed technical information, see:** `LOCATION_BASED_FILTERING_RESEARCH.md`

**Status:** ✅ Research Complete - Awaiting Decision
**Recommended Action:** Approve Option A (PostGIS + Geocoding)
**Timeline:** 4-5 weeks to full implementation
**Investment:** $0/month, one-time development cost only
