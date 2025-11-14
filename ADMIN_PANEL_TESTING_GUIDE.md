# 🎯 ADMIN PANEL TESTING GUIDE
**Complete Testing Checklist for Enhanced Admin Panel**

---

## 📦 SETUP INSTRUCTIONS

### 1. Pull Latest Changes
```bash
cd /path/to/MIT_PROJECTS
git pull origin claude/remember-hat-011CV5CDH3CzfNd9k2hkohga
```

### 2. Apply Database Migration
```bash
python manage.py migrate
```

This adds the `profile_picture` field to the database.

### 3. Create Media Directory
```bash
mkdir -p media/profile_pictures
```

### 4. Start Development Server
```bash
python manage.py runserver
```

---

## ✅ FEATURE TESTING CHECKLIST

### 🎨 1. MODERN FLAT DESIGN
**What to Check:**
- [ ] Open http://127.0.0.1:8000/admin-panel/
- [ ] Verify clean, modern design with flat colors
- [ ] Check PNP blue theme throughout
- [ ] Verify smooth hover effects on buttons
- [ ] Check card designs with subtle shadows
- [ ] Verify consistent spacing everywhere

**Expected Result:** Professional, clean, modern interface with PNP colors

---

### 📱 2. RESPONSIVE SIDEBAR

#### Desktop Test (> 768px width)
- [ ] Open admin panel on desktop
- [ ] Sidebar should be visible on left
- [ ] Sidebar should stay fixed while scrolling
- [ ] Click different menu items
- [ ] Active page should be highlighted in blue

**Expected:** Fixed sidebar, always visible, smooth scrolling

#### Mobile Test (≤ 768px width)
- [ ] Open DevTools (F12)
- [ ] Click device toolbar (Toggle device emulation)
- [ ] Resize to mobile width (e.g., iPhone 12)
- [ ] Look for hamburger menu (☰) in navbar
- [ ] Click hamburger menu
- [ ] **Expected:** Sidebar slides in from left
- [ ] Click overlay (dark background)
- [ ] **Expected:** Sidebar closes
- [ ] Open sidebar again
- [ ] Click any menu link
- [ ] **Expected:** Sidebar closes, page navigates

**Expected:** Smooth sliding sidebar with dark overlay

---

### 🔒 3. PASSWORD PROTECTION FOR SUPERUSER

#### Test Setup
1. Create test superuser account:
```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
user = User.objects.create_user('testsuper', password='testpass123')
user.is_superuser = True
user.is_staff = True
user.save()
exit()
```

#### Test Password Protection
- [ ] Login as admin to /admin-panel/
- [ ] Go to Users → Find 'testsuper' (or any superuser)
- [ ] **Expected:** Yellow warning banner at top
- [ ] **Expected:** Red "SUPERUSER" badge with crown icon
- [ ] Try to edit Basic Information
- [ ] **Expected:** Password modal pops up
- [ ] Enter WRONG password
- [ ] **Expected:** Red error message "Incorrect password"
- [ ] Enter CORRECT password
- [ ] **Expected:** Modal closes, changes saved
- [ ] Try to edit Permissions section
- [ ] **Expected:** Password modal appears again

**Expected:** Cannot edit superuser without password confirmation

#### Test Regular User (No Password Required)
- [ ] Go to Users → Find non-superuser account
- [ ] **Expected:** NO yellow warning banner
- [ ] **Expected:** NO password modal
- [ ] Edit and save directly
- [ ] **Expected:** Saves without password

**Expected:** Regular users can be edited without password

---

### 🖼️ 4. PROFILE PICTURE FUNCTIONALITY

#### Upload Profile Picture
- [ ] Go to Users → Create New User
- [ ] Fill in all required fields
- [ ] Scroll to "Profile Picture" section
- [ ] Click "Choose File"
- [ ] Select an image (JPG or PNG, under 5MB)
- [ ] **Expected:** Live preview shows selected image
- [ ] Click "Create User"
- [ ] **Expected:** User created with profile picture

#### View Profile Picture in Admin
- [ ] Go back to Users list
- [ ] Find user you just created
- [ ] **Expected:** Profile picture shows in table (40px circle)
- [ ] Go to Dashboard
- [ ] **Expected:** Profile picture in Recent Activity
- [ ] Look at navbar (top right)
- [ ] **Expected:** Your profile picture shows (32px circle)

#### Test Fallback (No Picture)
- [ ] Create user WITHOUT uploading picture
- [ ] **Expected:** Shows first letter of username in colored circle

#### Edit Profile Picture
- [ ] Go to existing user detail page
- [ ] Scroll to "Profile Picture" section
- [ ] **Expected:** Current picture displayed
- [ ] **Expected:** Checkbox "Remove current picture"
- [ ] Upload new picture
- [ ] **Expected:** Preview shows new image
- [ ] Save changes
- [ ] **Expected:** New picture appears everywhere

#### Test File Validation
- [ ] Try to upload file > 5MB
- [ ] **Expected:** Error "File size too large!"
- [ ] Try to upload non-image file (PDF, TXT, etc.)
- [ ] **Expected:** Error "Please select a valid image file!"

---

### 👥 5. SUPER ADMIN ROLE PERMISSIONS

#### Test Setup
Create a super_admin role user (without Django superuser):

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from accidents.models import UserProfile

user = User.objects.create_user('juandelacruz', password='test123')
user.first_name = 'Juan'
user.last_name = 'Dela Cruz'
user.is_staff = False  # NOT Django staff
user.is_superuser = False  # NOT Django superuser
user.save()

profile = UserProfile.objects.create(
    user=user,
    badge_number='PNP-2024-001',
    rank='PCAPTAIN',
    role='super_admin',  # Super Admin ROLE
    mobile_number='09171234567',
    region='CARAGA',
    province='Agusan del Norte'
)
exit()
```

#### Test Super Admin Access
- [ ] Logout from current account
- [ ] Login as 'juandelacruz' / 'test123'
- [ ] Go to /admin-panel/
- [ ] **Expected:** Can access admin panel
- [ ] Look at sidebar
- [ ] **Expected:** "User Management" menu is visible
- [ ] Click "User Management"
- [ ] **Expected:** Can view all users
- [ ] Try to create new user
- [ ] **Expected:** Can create users
- [ ] Try to edit existing user
- [ ] **Expected:** Can edit users
- [ ] Try to access /admin/ (Django admin)
- [ ] **Expected:** CANNOT access (403 Forbidden or login required)

**Expected:** Super admin role can manage users in custom admin panel but NOT Django admin

---

### 🔐 6. PASSWORD CHANGE FOR NEW USERS

#### Test New User Flow
- [ ] Create new user in admin panel
- [ ] Logout
- [ ] Login with new user credentials
- [ ] **Expected:** Redirected to /change-password/
- [ ] See password change form with:
  - [ ] Current password field
  - [ ] New password field
  - [ ] Confirm password field
  - [ ] Password strength indicator
- [ ] Enter passwords that don't match
- [ ] **Expected:** Red border on confirm field
- [ ] Enter matching passwords
- [ ] **Expected:** Green border, "Passwords match" message
- [ ] Submit form
- [ ] **Expected:** Redirected to dashboard
- [ ] Logout and login again
- [ ] **Expected:** Goes straight to dashboard (no password change required)

---

### 📊 7. DASHBOARD & STATS

- [ ] Go to /admin-panel/
- [ ] Check stat cards at top
- [ ] **Expected:** Total Users, Active Users, Superusers, Recent Logins
- [ ] Verify numbers are correct
- [ ] Check Recent Activity table
- [ ] **Expected:** Shows user profile pictures
- [ ] **Expected:** Shows latest actions
- [ ] Verify dates and times are correct

---

### 🔍 8. AUDIT LOGS

- [ ] Click "Audit Logs" in sidebar
- [ ] **Expected:** Shows all system activities
- [ ] Verify password verification attempts are logged
- [ ] Verify user edits are logged
- [ ] Check filters work (Action, Severity, Date)
- [ ] Search for specific user
- [ ] **Expected:** Results filtered correctly

---

### 🎭 9. USER MANAGEMENT FEATURES

#### Username Field
- [ ] Go to any user detail page
- [ ] Look at Username field
- [ ] **Expected:** Always disabled (greyed out)
- [ ] **Expected:** Text says "Username cannot be changed"

#### Province & Station Dropdowns
- [ ] Create or edit user
- [ ] Check Province dropdown
- [ ] **Expected:** Shows 6 options:
  - Agusan del Norte
  - Agusan del Sur
  - Butuan City
  - Dinagat Islands
  - Surigao del Norte
  - Surigao del Sur
- [ ] Select "Agusan del Norte"
- [ ] Check Station dropdown
- [ ] **Expected:** Shows 11 Agusan del Norte stations
- [ ] Change to "Butuan City"
- [ ] **Expected:** Shows 5 Butuan City PS stations
- [ ] Verify stations update dynamically

#### Password Confirmation Fields
- [ ] Create new user
- [ ] Enter password: "test1234"
- [ ] Enter confirm password: "test5678" (different)
- [ ] **Expected:** Red border, "Passwords do not match"
- [ ] Change confirm to "test1234" (matching)
- [ ] **Expected:** Green border, "Passwords match"

---

## 🎨 VISUAL DESIGN CHECKLIST

### Colors
- [ ] Primary blue: #003087 (PNP official blue)
- [ ] Red accents: #DC143C (PNP red)
- [ ] Success green: #10B981
- [ ] Clean white cards
- [ ] Light gray background: #F9FAFB

### Typography
- [ ] Inter font loaded and used
- [ ] Clear font hierarchy
- [ ] Readable font sizes
- [ ] Proper line heights

### Spacing
- [ ] Consistent padding everywhere
- [ ] Clean margins between elements
- [ ] No cramped sections
- [ ] Professional spacing

### Animations
- [ ] Smooth button hovers (lift effect)
- [ ] Sidebar slide animation (300ms)
- [ ] Modal fade-in animation
- [ ] Form field focus effects
- [ ] All animations smooth (no jank)

---

## 🐛 COMMON ISSUES & FIXES

### Issue: Profile Pictures Not Showing
**Fix:**
```bash
# Make sure media directory exists
mkdir -p media/profile_pictures
chmod 755 media/profile_pictures

# Check settings.py has:
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

### Issue: Password Modal Not Appearing
**Fix:**
- Clear browser cache (Ctrl+Shift+Del)
- Hard refresh page (Ctrl+F5)
- Check browser console for JavaScript errors

### Issue: Migration Error
**Fix:**
```bash
python manage.py makemigrations accidents
python manage.py migrate accidents
```

### Issue: Sidebar Not Sliding on Mobile
**Fix:**
- Open DevTools (F12)
- Click device toolbar
- Refresh page
- Try hamburger menu again

### Issue: "User has no profile"
**Fix:**
```bash
python manage.py shell
```
```python
from django.contrib.auth.models import User
from accidents.models import UserProfile

# Find user without profile
user = User.objects.get(username='username_here')

# Create profile
profile = UserProfile.objects.create(
    user=user,
    badge_number='TEMP-001',
    mobile_number='09171234567',
    role='traffic_officer'
)
```

---

## 📸 SCREENSHOT CHECKLIST

Take screenshots of these for documentation:

1. **Desktop View**
   - [ ] Dashboard with stats cards
   - [ ] User management table with profile pictures
   - [ ] User detail page
   - [ ] Sidebar navigation

2. **Mobile View**
   - [ ] Hamburger menu button
   - [ ] Sidebar opened on mobile
   - [ ] Dashboard on mobile
   - [ ] User list on mobile

3. **Security Features**
   - [ ] Password confirmation modal
   - [ ] Superuser warning banner
   - [ ] Password strength indicator

4. **Profile Pictures**
   - [ ] Upload preview
   - [ ] Pictures in user table
   - [ ] Pictures in navbar
   - [ ] Pictures in activity log

---

## ✅ FINAL VERIFICATION

All these should be TRUE:

- [ ] ✅ Admin panel loads without errors
- [ ] ✅ Design is modern, flat, and clean
- [ ] ✅ Sidebar works on desktop (fixed)
- [ ] ✅ Sidebar works on mobile (sliding)
- [ ] ✅ Password modal works for superusers
- [ ] ✅ Profile pictures upload successfully
- [ ] ✅ Profile pictures show everywhere
- [ ] ✅ Super admin role can manage users
- [ ] ✅ New users must change password
- [ ] ✅ No console errors
- [ ] ✅ No 404 errors
- [ ] ✅ All links work
- [ ] ✅ All forms submit correctly
- [ ] ✅ Mobile navigation works perfectly
- [ ] ✅ Animations are smooth

---

## 🎯 PERFORMANCE CHECKLIST

- [ ] Page loads in < 2 seconds
- [ ] Images load quickly
- [ ] No layout shift (CLS)
- [ ] Animations are GPU-accelerated
- [ ] No memory leaks
- [ ] Mobile performance is good
- [ ] Works on slow connections

---

## 🌐 BROWSER COMPATIBILITY

Test on:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if on Mac)
- [ ] Mobile Chrome (Android)
- [ ] Mobile Safari (iOS)

---

## 🎉 SUCCESS CRITERIA

**The admin panel is ready for production if:**

1. ✅ All features work as described
2. ✅ No errors in browser console
3. ✅ Design looks professional
4. ✅ Mobile experience is smooth
5. ✅ Security features work correctly
6. ✅ Performance is good
7. ✅ All tests pass

---

## 📞 SUPPORT

If you encounter any issues:

1. Check browser console for errors
2. Check Django logs in terminal
3. Clear browser cache
4. Try incognito/private mode
5. Verify database migration ran
6. Check file permissions on media folder

---

**Version:** 1.0
**Last Updated:** 2025-11-14
**Branch:** claude/remember-hat-011CV5CDH3CzfNd9k2hkohga
