# Onboarding App

## Overview

The **Onboarding** app provides a personalized setup experience for new users of the Vineyard Group Fellowship platform. It guides users through initial account configuration with different flows for group members and group leaders.

---

## Responsibilities

1. **Personalized Onboarding Flows** - Different experiences for members (6 steps) vs leaders (9 steps)
2. **Progress Tracking** - Monitor completion status and time spent
3. **Leadership Profile Setup** - Configure ministry experience and group preferences for leaders
4. **Community Preferences** - Set up fellowship participation preferences
5. **Feedback Collection** - Gather user feedback on onboarding experience
6. **Analytics** - Track onboarding metrics and drop-off points

---

## Key Features

- **Role-Based Flows**: Automatic detection of user role (member vs leader)
- **Step-by-Step Process**: Clear progression through required and optional steps
- **Progress Persistence**: Save progress and resume later
- **Time Tracking**: Monitor time spent on each step
- **Welcome Messages**: Personalized greetings based on user type
- **Feedback System**: Collect step-by-step and overall feedback

---

## Available Endpoints

### Base URL
```
/api/v1/onboarding/
```

### Endpoints

| Method | Endpoint | Description | Auth Required | Tags |
|--------|----------|-------------|---------------|------|
| GET | `/flow/` | Get personalized onboarding flow | Yes | Onboarding |
| GET | `/step/` | Get current onboarding status | Yes | Onboarding |
| PATCH | `/step/` | Update onboarding step | Yes | Onboarding |
| GET | `/community-preferences/` | Get community preferences | Yes | Onboarding |
| POST | `/community-preferences/` | Set community preferences | Yes | Onboarding |
| GET | `/leadership-profile/` | Get leadership profile | Yes (Leaders) | Onboarding |
| POST | `/leadership-profile/` | Save leadership profile | Yes (Leaders) | Onboarding |
| POST | `/complete/` | Complete onboarding | Yes | Onboarding |
| POST | `/feedback/` | Submit step feedback | Yes | Onboarding |

---

## Onboarding Flows

### Member Flow (5-8 minutes, 6 steps)
1. **Welcome** - Introduction to Vineyard Group Fellowship
2. **Profile Setup** - Basic profile information
3. **Privacy Settings** - Privacy preferences
4. **Community Preferences** - Fellowship participation preferences
5. **Notifications** - Notification settings
6. **Completed** - Onboarding complete

### Leader Flow (10-15 minutes, 9 steps)
1. **Welcome** - Introduction for group leaders
2. **Profile Setup** - Basic profile information
3. **Privacy Settings** - Privacy preferences
4. **Leadership Information** - Ministry experience and background
5. **Group Preferences** - Group leadership preferences
6. **Community Preferences** - Fellowship participation preferences
7. **Notifications** - Notification settings
8. **Guidelines Agreement** - Leadership guidelines and policies
9. **Completed** - Onboarding complete

---

## Models

### LeadershipProfile
```python
class LeadershipProfile(models.Model):
    """Leadership profile for group leaders."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ministry_experience_years = models.PositiveIntegerField()
    ministry_interests = ArrayField(models.CharField(max_length=100))
    preferred_group_size = models.CharField(max_length=20)
    meeting_frequency_preference = models.CharField(max_length=20)
    leadership_topics = ArrayField(models.CharField(max_length=200))
    general_availability = models.TextField()
    max_group_capacity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### OnboardingProgress
```python
class OnboardingProgress(models.Model):
    """Track user onboarding progress."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    steps_completed = models.JSONField(default=dict)
    total_steps = models.PositiveIntegerField(default=0)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    time_spent_minutes = models.PositiveIntegerField(default=0)
    dropped_off_at_step = models.CharField(max_length=50, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
```

### OnboardingFeedback
```python
class OnboardingFeedback(models.Model):
    """Collect feedback on onboarding steps."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    step_name = models.CharField(max_length=50)
    rating = models.PositiveIntegerField()
    feedback_text = models.TextField(blank=True)
    was_helpful = models.BooleanField(default=True)
    was_confusing = models.BooleanField(default=False)
    suggestions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## Integration with Other Apps

### Authentication
- Requires authenticated user
- Uses JWT token authentication
- Checks `leadership_info.can_lead_group` for role detection

### Profiles
- Saves community preferences to user profile
- Links to UserProfileBasic model
- Updates profile completion status

---

## Frontend Integration

For complete frontend integration guide, see:
- [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md)

Quick example:
```javascript
// Get onboarding flow
const response = await fetch('/api/v1/onboarding/flow/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const flow = await response.json();

// Update step progress
await fetch('/api/v1/onboarding/step/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    step_name: 'profile_setup',
    time_spent_minutes: 3,
    completed: true
  })
});
```

---

## Configuration

### Environment Variables
No specific environment variables required.

### Settings
```python
INSTALLED_APPS = [
    'onboarding',
]
```

---

## Related Documentation

- [Frontend Integration Guide](./FRONTEND_INTEGRATION.md) - Complete API integration guide
- [Onboarding Analysis](./ONBOARDING_ANALYSIS.md) - Technical analysis and design decisions
- [Authentication README](../authentication/README.md)
- [Profiles README](../profiles/README.md)

---

**Last Updated:** October 31, 2025
    title = models.CharField(max_length=100)
    description = models.TextField()
    required = models.BooleanField(default=True)
    order = models.IntegerField()
```

## Onboarding Flow Steps

### For Recovery Seekers

1. **Welcome & Purpose Selection**

   - Select "Seeking Recovery Support"
   - Brief platform introduction

2. **Recovery Approach Preferences**

   - Choose religious/secular/mixed approach
   - Select faith tradition if applicable
   - Set religious content preference

3. **Basic Profile Setup**

   - Display name (optional)
   - Bio (optional)
   - Privacy settings

4. **Recovery Information** (Optional)

   - Recovery stage
   - Sobriety date
   - Recovery goals (private)

5. **Community Preferences**
   - Notification settings
   - Communication preferences
   - Crisis support setup

### For Support Providers

1. **Welcome & Purpose Selection**

   - Select "Providing Recovery Support"
   - Supporter role explanation

2. **Qualification Setup**

   - Recovery experience years
   - Addiction types they can support
   - Communication methods preference
   - Background verification initiation

3. **Supporter Profile**

   - Professional background
   - Support approach
   - Availability preferences

4. **Training & Verification**
   - Platform guidelines acknowledgment
   - Safety protocols understanding
   - Background check process

## Current Implementation Analysis

### Recent Issues Fixed

- Supporter background debugging functionality
- Supporter qualification system improvements
- Recovery approach preference setup

### Integration Points

- **Authentication App**: User purpose system integration
- **Profiles App**: Profile setup during onboarding
- **Privacy App**: Privacy preference setup
- **Recovery Data**: Recovery goal and stage setup

## File Structure

```
onboarding/
├── models.py         # Onboarding progress and step models
├── serializers.py    # Onboarding flow serializers
├── views.py         # Onboarding API endpoints
├── utils.py         # Onboarding utilities
├── permissions.py   # Onboarding-specific permissions
└── README.md        # This file
```

## Dependencies

- Authentication app (user purpose system)
- Profiles app (profile creation)
- Privacy app (privacy settings)
- Core app (utilities)

## Business Logic

### Onboarding Validation

- Ensure required steps are completed
- Validate user input for each step
- Handle edge cases (returning users, etc.)

### Progress Tracking

- Save progress after each step
- Allow resuming incomplete onboarding
- Track completion timestamps
- Analytics on drop-off points

### Supporter Qualification Flow

- Background information collection
- Verification process initiation
- Qualification status tracking
- Integration with support matching

## Security Considerations

- **Privacy**: Onboarding data may be sensitive
- **Validation**: Ensure supporter qualifications are verified
- **Rate Limiting**: Prevent onboarding abuse
- **Data Protection**: Secure storage of qualification information

## Performance Considerations

- **Step Caching**: Cache onboarding step definitions
- **Progress Optimization**: Efficient progress tracking
- **Async Processing**: Background verification processes
- **Mobile Optimization**: Quick step completion on mobile

## Testing Requirements

- Test complete onboarding flows
- Test partial completion and resumption
- Validate supporter qualification flow
- Test error handling and edge cases
- Performance testing for mobile users

## Analytics & Monitoring

- Track onboarding completion rates
- Monitor drop-off points
- Measure time to complete onboarding
- A/B testing for onboarding improvements

## Usage Examples

### Starting Onboarding

```python
from onboarding.services import OnboardingService

service = OnboardingService(user)
progress = service.start_onboarding()
```

### Completing a Step

```python
step_data = {
    'user_purpose': 'seeking_recovery',
    'recovery_approach': 'mixed'
}
service.complete_step('purpose_selection', step_data)
```

### Checking Progress

```python
progress = service.get_progress()
if progress.is_completed:
    redirect_to_dashboard()
else:
    continue_onboarding(progress.current_step)
```

## Future Enhancements

- **Adaptive Onboarding**: Customize flow based on user responses
- **Skip Options**: Allow experienced users to skip certain steps
- **Social Integration**: Import information from social profiles
- **Gamification**: Progress indicators and completion rewards

## Notes

- This app is crucial for user retention and proper platform setup
- The onboarding experience significantly impacts user engagement
- Supporter qualification flow is critical for platform safety
- Mobile-first design is essential for accessibility

The onboarding app serves as the user's first impression of the platform and
sets up their entire experience.
