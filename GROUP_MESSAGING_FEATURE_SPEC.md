# Group Messaging Feature Specification

## Overview

The Group Messaging feature provides a safe, structured communication platform for Vineyard Group Fellowship members to support each other spiritually, share testimonies, and engage in meaningful faith-based discussions within their Christian fellowship groups.

---

## Core Principles

### Communication Style
- **Asynchronous discussion boards** - More manageable and thoughtful than real-time chat
- **Structured and moderated** - Leader-initiated topics with member participation
- **Privacy-first** - All group communication stays within the group
- **Inspiration-focused** - Success stories can be shared publicly to inspire others

### User Roles & Permissions

**Group Leaders:**
- ✅ Can create discussion topics
- ✅ Can moderate/delete inappropriate content
- ✅ Can pin important messages
- ✅ Can share resources
- ❌ Cannot temporarily mute members (permanent removal only if necessary)

**Group Members:**
- ✅ Can comment on discussions
- ✅ Can post check-ins and milestones
- ✅ Can react to posts
- ✅ Can request prayer/support
- ✅ Can opt to share their success stories publicly

**Co-Leaders:**
- ✅ Same permissions as Group Leaders

---

## Feature Architecture

### Tab Structure

The messaging feature will use a **two-tab layout** within the Group Details page:

```
┌─────────────────────────────────────┐
│  Details  |  Messages               │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────┬──────────────┐       │
│  │  Feed    │ Discussions  │       │
│  └──────────┴──────────────┘       │
│                                     │
│  [Content Area]                     │
│                                     │
│         [+ Quick Action Button]     │
└─────────────────────────────────────┘
```

---

## Tab 1: Feed (Home View)

### Purpose
Real-time activity stream showing recent group interactions, check-ins, and support requests.

### Content Types

#### 1. Prayer Requests
- **Format**: Prayer needs and requests (character limit: 500)
- **Types**: Personal, Family, Community, Thanksgiving
- **Visibility**: Group members only
- **Urgency**: Normal / Urgent
- **Example**: "Please pray for my family as we navigate this difficult season. Trusting God's timing 🙏"

#### 2. Testimonies & Praises
- **Manual** members share how God is working in their lives
- **Visibility**: Group only, with option to share publicly
- **Reactions**: 👍 ❤️ 🙏 🎉
- **Example**: "🎉 God answered my prayer! Got the job I've been praying about for months! Praise the Lord!"

#### 3. Scripture Sharing & Reflections
- **Types**:
  - Daily verse reflections
  - Personal insights from Bible study
  - Encouraging scriptures
  - Devotional thoughts
- **Notifications**: Optional for group members
- **Example**: "Philippians 4:13 has been speaking to me this week - I can do all things through Christ who strengthens me!"

#### 4. Recent Activity
- Latest discussion comments
- New members joining
- Meeting/Bible study reminders
- Ministry opportunities
- Leader announcements

### Feed UI Components

```
┌─────────────────────────────────────┐
│ 📅 Bible Study: Tomorrow 7PM        │
├─────────────────────────────────────┤
│                                     │
│ 🎉 John • Testimony                 │
│ "God has been faithful! My wife and │
│  I celebrated 10 years of marriage. │
│  All glory to Him!"                 │
│ 👍 12  ❤️ 8  🙏 15  💬 5            │
│ 2 hours ago                         │
│                                     │
├─────────────────────────────────────┤
│                                     │
│ 🙏 Sarah • Prayer Request           │
│ "Big job interview tomorrow.        │
│  Nervous but trusting God."         │
│ 👍 5  ❤️ 3  🙏 18  💬 3             │
│ 4 hours ago                         │
│                                     │
├─────────────────────────────────────┤
│                                     │
│ 💬 Mike commented on "Walking in    │
│    Faith Daily"                     │
│ 6 hours ago                         │
│                                     │
└─────────────────────────────────────┘
```

---

## Tab 2: Discussions (Threaded)

### Purpose
Deeper, organized conversations on specific topics initiated by group leaders.

### Features

#### 1. Leader-Started Topics
- **Only leaders/co-leaders** can create new discussion threads
- **Categories**:
  - 📖 Bible Study & Scripture
  - 🙏 Prayer & Worship
  - 📚 Christian Resources
  - ✝️ Faith & Discipleship
  - � Spiritual Growth
  - 🎉 Testimonies & Praises
  - 🤝 Ministry & Service
  - 📢 Announcements

#### 2. Thread Structure
- **Title** (required, max 100 characters)
- **Category** (required, from predefined list)
- **Description** (optional, max 1000 characters)
- **Attachments** (images, documents - optional)
- **Pin status** (leaders can pin important topics)

#### 3. Comments
- All active group members can comment
- Nested replies (1 level deep)
- Edit own comments (within 15 minutes)
- Delete own comments
- Leaders can delete any comment

#### 4. Reactions
- 👍 Helpful
- ❤️ Love/Support
- 🙏 Praying
- 🎉 Celebrate
- 💡 Insightful

#### 5. Searchable Archive
- Search by keyword
- Filter by category
- Sort by recent/most engaged/pinned
- View archived discussions

### Discussion UI Components

```
┌─────────────────────────────────────┐
│ 📌 PINNED                           │
│                                     │
│ 📖 Bible Study: Romans 8            │
│ By Leader Mike • 3 days ago         │
│ "This week we're studying Romans 8, │
│ let's discuss..."                   │
│ 💬 24 comments  👍 15  ❤️ 12        │
│                                     │
├─────────────────────────────────────┤
│                                     │
│ ✝️ Walking in Faith Daily           │
│ By Leader Sarah • 1 week ago        │
│ "How can we practice faith in our   │
│ everyday lives?"                    │
│ 💬 18 comments  👍 10  ❤️ 8         │
│                                     │
├─────────────────────────────────────┤
│                                     │
│ 🤝 Community Service Opportunity    │
│ By Co-Leader Tom • 2 weeks ago      │
│ "Join us in serving at the local    │
│ shelter..."                         │
│ 💬 31 comments  👍 22  💡 15        │
│                                     │
└─────────────────────────────────────┘
```

---

## Quick Actions (Floating Button)

### Location
Bottom-right corner of the Messages tab (both Feed and Discussions views)

### Actions Menu

```
          ┌─────────────────────────┐
          │ 🙏 Request Prayer       │
          ├─────────────────────────┤
          │ � Share Testimony      │
          ├─────────────────────────┤
          │ 📖 Share Scripture      │
          └─────────────────────────┘
                    ▲
              ┌─────┴─────┐
              │     +     │  ← Floating Action Button
              └───────────┘
```

### Quick Action Forms

**Request Prayer:**
- Prayer category: Personal / Family / Ministry / Thanksgiving
- Text input (500 char limit)
- Urgency: Normal / Urgent
- Anonymous toggle
- Submit button

**Share Testimony:**
- Testimony type: Answered prayer / God's faithfulness / Personal growth / Other
- Description (required, 1000 char limit)
- Share publicly toggle
- Submit button

**Share Scripture:**
- Bible verse reference (e.g., John 3:16)
- Personal reflection (optional, 500 char limit)
- Auto-fetch verse text from Bible API
- Submit button

---

## Integration Points

### 1. Meeting Schedules
- **Automatic Reminders**: Posted to Feed 24 hours before Bible study/fellowship meeting
- **Meeting Prep Discussions**: Auto-created weekly by system with study materials
- **Post-Meeting Reflection**: Leader can create discussion after meeting
- **Attendance Tracking**: Optional

### 2. Spiritual Growth Tracking
- **Bible Reading Plans**: Track progress through reading plans
- **Scripture Memory**: Track memorized verses
- **Prayer Journal Integration**: Link prayer requests to answered prayers
- **Encouragement Triggers**: System suggests engagement if member hasn't participated in X days

### 3. Testimony Sharing
- **Public Inspiration Board**: Separate section for publicly shared testimonies
- **Permission-Based**: Members opt-in to share specific testimonies publicly
- **Anonymization Option**: Share publicly but anonymously
- **Cross-Group Inspiration**: Public testimonies visible to all app users

---

## Data & Privacy

### Message History Retention

**Active Discussions:**
- Kept indefinitely while group is active
- Accessible to all current group members

**Archived Discussions:**
- Older discussions (6+ months) moved to archive
- Still searchable and accessible
- Can be restored to active view by leaders

**Deleted Content:**
- Soft delete (30-day recovery period for leaders)
- Permanent delete after 30 days
- User-deleted content removed immediately from view

**Member Departure:**
- When member leaves group, their posts remain (anonymized)
- Member can request full deletion of their content
- Leaders notified of deletion requests

### Export Capability

**For Accountability Partners:**
- Member can generate PDF export of their own posts/check-ins
- Date range selector
- Includes: Check-ins, milestones, discussion participation
- Excludes: Others' private content, support requests

**For Leaders:**
- Export group statistics (engagement metrics)
- Cannot export individual member data without consent
- Group-level reports only

**For Members:**
- Export their own complete activity history
- Includes all their posts, comments, reactions
- Downloadable as JSON or PDF

### Privacy Controls

**Content Visibility:**
- Default: Group members only
- Optional: Share specific posts publicly (with member consent)
- Success stories: Opt-in public sharing

**Anonymous Posting:**
- Available for sensitive topics
- "Anonymous Member" displayed instead of name
- Leaders can see true identity for moderation

**Data Security:**
- All messages encrypted in transit (HTTPS)
- Encrypted at rest in database
- No third-party access
- Compliant with data protection regulations

---

## Implementation Phases

### Phase 1: MVP (Core Features)

**Timeline:** 4-6 weeks

**Deliverables:**

1. **Discussion Threads**
   - Leader-only topic creation
   - Title, category, description
   - Pin/unpin functionality
   - Basic text formatting (bold, italic, lists)

2. **Comments System**
   - All members can comment on threads
   - Single-level threading (reply to main post)
   - Edit own comments (15-min window)
   - Delete own comments

3. **Basic Reactions**
   - 👍 Helpful
   - ❤️ Love/Support
   - 🙏 Praying
   - Track reaction counts
   - One reaction per user per post

4. **Feed View**
   - Chronological activity stream
   - Show recent discussions
   - Display new comments
   - Simple refresh mechanism

5. **Moderation Tools**
   - Leaders can delete any comment
   - Leaders can delete discussions
   - Simple content reporting (flag for review)

**Technical Requirements:**
- Backend API endpoints for discussions/comments
- Real-time activity feed
- Role-based permissions
- Database schema for messages/reactions

---

### Phase 2: Enhanced Engagement

**Timeline:** 6-8 weeks after Phase 1

**Deliverables:**

1. **Scripture Sharing System**
   - Quick scripture post form
   - Bible verse lookup (integration with Bible API)
   - Personal reflection field
   - Daily verse suggestions
   - Favorite verses library

2. **Testimony & Praise Tracking**
   - Testimony categories (answered prayer, spiritual growth, etc.)
   - Praise reports
   - Custom testimony creation
   - Testimony notification system
   - Share publicly toggle

3. **Direct Leader Messaging**
   - Private DM to group leaders
   - Urgent support requests
   - Crisis escalation pathway
   - Leader notification system
   - Message threading

4. **Enhanced Feed**
   - Prayer request categories
   - Testimony section
   - Scripture reflections
   - Filter by content type
   - Mark as read/unread
   - Notification preferences

5. **Meeting Integration**
   - Link discussions to Bible study schedule
   - Pre-meeting reminders in feed with study materials
   - Post-meeting reflection prompts
   - Optional attendance tracking

**Technical Requirements:**
- User progress tracking database
- Notification service (email/push)
- Private messaging infrastructure
- Calendar integration API

---

### Phase 3: Advanced Features

**Timeline:** 8-10 weeks after Phase 2

**Deliverables:**

1. **Anonymous Posting**
   - Toggle for anonymous posts
   - Leader visibility override (for moderation)
   - Anonymous comment support
   - Privacy safeguards

2. **Resource Library**
   - Leader-curated resources
   - Categories: Articles, Videos, Books, Local Services
   - Bookmark/save resources
   - Share resources in discussions
   - External link validation

3. **Advanced Search & Archive**
   - Full-text search across all content
   - Filter by date, category, member, reactions
   - Tag system for discussions
   - Saved searches
   - Archive old discussions (6+ months)
   - Restore from archive

4. **Push Notifications**
   - Configurable notification preferences
   - Urgent prayer request alerts
   - New testimonies
   - Discussion replies
   - Bible study reminders
   - Digest mode (daily/weekly summary)
   - Quiet hours setting

5. **Public Testimonies**
   - Dedicated public inspiration section
   - Member opt-in required
   - Anonymization option
   - Cross-group visibility
   - Moderation queue for public posts
   - Testimony templates

6. **Export & Analytics**
   - Member activity export (PDF/JSON)
   - Accountability partner reports
   - Group engagement statistics
   - Leader dashboard analytics
   - Progress charts

7. **Rich Media Support**
   - Image attachments (with content moderation)
   - Document uploads (PDF, DOCX)
   - Link previews
   - Voice notes (optional)
   - Inspirational quote graphics

8. **Accessibility Features**
   - Screen reader optimization
   - Keyboard navigation
   - High contrast mode
   - Font size adjustments
   - Translation support (future)

**Technical Requirements:**
- CDN for media storage
- Content moderation service
- Analytics platform integration
- Advanced notification infrastructure
- Search indexing service
- Export generation service

---

## Success Metrics

### Engagement Metrics
- Daily active users per group
- Average posts/comments per week
- Reaction engagement rate
- Check-in completion rate
- Discussion participation rate

### Prayer Metrics
- Response time to prayer requests
- Prayer answered tracking
- Prayer participation rate
- Leader engagement rate

### Retention Metrics
- Member retention rate
- Group activity longevity
- Return visit frequency
- Feature adoption rate

### Testimony Metrics
- Total testimonies shared
- Testimony engagement rate
- Public vs. private testimony share rate
- Scripture sharing frequency

---

## Technical Architecture Overview

### Frontend Components
```
src/
  pages/
    Dashboard/
      GroupDetailsPage/
        components/
          GroupMessages/
            Feed/
              PrayerRequestCard.tsx
              TestimonyCard.tsx
              ScriptureCard.tsx
              ActivityItem.tsx
            Discussions/
              DiscussionList.tsx
              DiscussionThread.tsx
              CommentSection.tsx
              ReactionBar.tsx
            QuickActions/
              QuickActionButton.tsx
              PrayerRequestForm.tsx
              TestimonyForm.tsx
              ScriptureShareForm.tsx
```

### Backend API Endpoints
```
/api/groups/:groupId/messages/
  GET    /feed                 # Get activity feed
  GET    /discussions          # List discussions
  POST   /discussions          # Create discussion (leaders only)
  GET    /discussions/:id      # Get single discussion
  DELETE /discussions/:id      # Delete discussion (leaders only)
  PATCH  /discussions/:id/pin  # Pin/unpin discussion

  POST   /discussions/:id/comments    # Add comment
  PATCH  /comments/:id                # Edit comment
  DELETE /comments/:id                # Delete comment

  POST   /reactions                   # Add reaction
  DELETE /reactions/:id               # Remove reaction

  POST   /check-ins                   # Post check-in
  POST   /support-requests            # Post support request
  POST   /milestones                  # Post milestone

  GET    /export                      # Export member data
```

### Database Schema (Conceptual)
```
discussions:
  - id
  - group_id
  - author_id (leader)
  - title
  - category
  - content
  - is_pinned
  - created_at
  - updated_at

comments:
  - id
  - discussion_id
  - author_id
  - content
  - parent_comment_id (for threading)
  - is_anonymous
  - created_at
  - updated_at

reactions:
  - id
  - target_id (discussion, comment, prayer, testimony, etc.)
  - target_type (enum: discussion, comment, prayer_request, testimony, scripture)
  - user_id
  - reaction_type (enum: helpful, love, pray, celebrate, insight, amen)
  - created_at

prayer_requests:
  - id
  - group_id
  - user_id
  - category (enum: personal, family, ministry, thanksgiving)
  - content
  - urgency (enum: normal, urgent)
  - is_anonymous
  - is_answered
  - answered_at
  - created_at

testimonies:
  - id
  - group_id
  - user_id
  - testimony_type (enum: answered_prayer, faithfulness, spiritual_growth, other)
  - title
  - description
  - is_public
  - created_at

scriptures:
  - id
  - group_id
  - user_id
  - verse_reference (e.g., "John 3:16")
  - verse_text
  - reflection
  - created_at
```

---

## Design Guidelines

### Visual Design Principles

**Color Scheme:**
- Use warm, welcoming colors from brand palette
- **Celebration/Testimony**: `--accent-warm` (#F4C77B)
- **Prayer/Worship**: Soft purple/blue tones
- **Urgent Prayer**: Gentle orange (not harsh)
- **Neutral**: `--surface-elevated` (#EAE6E1)

**Typography:**
- Clear, readable fonts
- Sufficient line height for easy reading
- Larger font for main content
- Smaller, muted text for metadata

**Spacing:**
- Generous whitespace for calm feel
- 4pt spacing system (var(--size-*))
- Clear visual separation between posts
- Comfortable touch targets (min 44px)

**Icons:**
- Use existing Icon component
- Consistent icon style throughout
- Meaningful icons for reactions
- Clear visual feedback

### Accessibility

- WCAG 2.1 AA compliant
- Keyboard navigation support
- Screen reader announcements
- Focus indicators
- Color is not sole indicator
- Alt text for images
- Semantic HTML structure

### Mobile Responsiveness

- Mobile-first design
- Touch-friendly interactions
- Bottom sheet modals for forms
- Swipe gestures (optional)
- Optimized for one-handed use
- Minimize scrolling friction

---

## Content Moderation Guidelines

### Leader Responsibilities

**Monitor for:**
- Inappropriate language/content
- False teaching or non-biblical content
- Spam or promotional content
- Harassment or bullying
- Divisive or controversial topics
- Privacy violations

**Action Steps:**
1. Review flagged content within 24 hours
2. Delete harmful content immediately
3. Contact member privately about violations
4. Document moderation actions
5. Escalate serious concerns to platform admins

### Automated Safeguards

- Keyword filtering (configurable)
- Link validation (prevent malicious links)
- Rate limiting (prevent spam)
- Image content scanning (optional)
- Profanity filter (gentle, configurable)

### Community Guidelines (Displayed to Users)

**Be Respectful:**
- Honor each person's journey
- No judgment or criticism
- Assume positive intent

**Be Supportive:**
- Offer encouragement
- Share from personal experience
- Listen more than advise

**Be Safe:**
- No sharing of personal contact info
- Stay grounded in biblical truth
- No medical or legal advice
- Report concerning content

**Be Authentic:**
- Share honestly but appropriately
- Respect confidentiality
- Use anonymous posting for sensitive topics

---

## Risk Mitigation

### Potential Risks & Solutions

**Risk: Members needing urgent prayer support**
- **Solution**: Urgent prayer request notification to all members
- **Solution**: Instant leader notification for urgent prayers
- **Solution**: Display church/pastoral care contact info prominently

**Risk: Content moderation burden on leaders**
- **Solution**: Start with smaller groups
- **Solution**: Co-leader support for moderation
- **Solution**: Automated filtering tools
- **Solution**: Community reporting system

**Risk: Privacy concerns with shared content**
- **Solution**: Clear privacy settings and indicators
- **Solution**: Anonymous posting option
- **Solution**: Member control over public sharing
- **Solution**: Easy content deletion

**Risk: Low engagement/adoption**
- **Solution**: Leader training on engagement
- **Solution**: Automated prompts and reminders
- **Solution**: Gamification (milestones, streaks)
- **Solution**: Integration with existing features

**Risk: Divisive or non-biblical content**
- **Solution**: Clear community guidelines on staying biblically grounded
- **Solution**: Quick reporting mechanism
- **Solution**: Leader moderation training on handling doctrinal questions
- **Solution**: Keyword alerts for potentially divisive topics

---

## Future Enhancements (Post-Phase 3)

### Possible Features
- Video/audio prayer messages
- Live group prayer/worship sessions (scheduled)
- Prayer partner matching
- Mentorship matching system
- Integration with Bible reading apps (YouVersion, Bible Gateway)
- Multi-language support
- AI-powered scripture suggestions
- Bible study tracking
- Group prayer challenges
- Integration with church calendar/events
- Sermon notes sharing
- Ministry team coordination tools

---
## Conclusion

This Group Messaging feature is designed to provide a **safe, supportive, and structured communication platform** that aligns with Vineyard Group Fellowship's mission of spiritual growth and Christian community. By combining an engaging activity feed with thoughtful discussion threads, we create a space where members can:

- ✅ Share their faith journey authentically
- ✅ Receive timely prayer support and encouragement
- ✅ Celebrate God's faithfulness together through testimonies
- ✅ Engage in meaningful biblical discussions
- ✅ Build spiritual accountability and community
- ✅ Access Christian resources and teaching
- ✅ Inspire others through testimonies of God's work
- ✅ Inspire others through their success

The phased implementation approach ensures we can **deliver value early** while iterating based on real user feedback and needs.

---

**Document Version:** 1.0
**Last Updated:** November 6, 2025
**Status:** Planning & Design Phase
**Next Steps:** Review with stakeholders → Technical feasibility analysis → Phase 1 development kickoff
