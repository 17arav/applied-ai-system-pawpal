import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler
from ai_assistant import generate_care_plan

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
# Initialize session state with Owner object
if "owner" not in st.session_state:
    st.session_state.owner = None

if "scheduler" not in st.session_state:
    st.session_state.scheduler = None
    
import os

# Auto-load saved data on startup
if st.session_state.owner is None and os.path.exists("data.json"):
    st.session_state.owner = Owner.load_from_json("data.json")
    st.session_state.scheduler = Scheduler(owner=st.session_state.owner)

# --- Sidebar: Reset / Clear All Data ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Clear All Data", type="secondary"):
        if os.path.exists("data.json"):
            os.remove("data.json")
        st.session_state.owner = None
        st.session_state.scheduler = None
        st.success("All data cleared! Refresh the page.")
        st.rerun()
    

st.title("🐾 PawPal+")
st.caption("A smart pet care management system")

# --- Owner Setup ---
st.subheader("👤 Owner Setup")
col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
with col2:
    available_time = st.number_input("Available time (minutes)", min_value=10, max_value=480, value=120)

if st.button("Create Owner"):
    st.session_state.owner = Owner(name=owner_name, available_time=available_time)
    st.session_state.scheduler = Scheduler(owner=st.session_state.owner)
    st.session_state.owner.save_to_json("data.json")
    st.success(f"Owner '{owner_name}' created with {available_time} minutes available!")

if st.session_state.owner is None:
    st.info("Please create an owner to get started.")
    st.stop()

st.divider()

# --- Add Pet ---
st.subheader("🐾 Add a Pet")
col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["Dog", "Cat", "Bird", "Fish", "Other"])
with col3:
    age = st.number_input("Age", min_value=0, max_value=30, value=2)

special_needs = st.text_input("Special needs (optional)", value="")

if st.button("Add Pet"):
    pet = Pet(name=pet_name, species=species, age=age, special_needs=special_needs)
    st.session_state.owner.add_pet(pet)
    st.success(f"Added {pet_name} the {species}!")
    st.session_state.owner.save_to_json("data.json")

# Show current pets
pets = st.session_state.owner.get_pets()
if pets:
    st.write(f"**Current pets ({len(pets)}):**")
    for p in pets:
        st.write(f"- {p.name} ({p.species}, age {p.age})")
else:
    st.info("No pets added yet.")

st.divider()

# --- Add Task ---
st.subheader("📋 Add a Task")
if not pets:
    st.info("Add a pet first before adding tasks.")
else:
    pet_names = [p.name for p in pets]
    col1, col2 = st.columns(2)
    with col1:
        selected_pet = st.selectbox("For which pet?", pet_names)
        task_name = st.text_input("Task name", value="Morning Walk")
        task_type = st.selectbox("Task type", ["walk", "feeding", "meds", "grooming", "enrichment", "other"])
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=30)
        priority = st.slider("Priority (1=low, 5=high)", min_value=1, max_value=5, value=3)
        recurring = st.checkbox("Recurring daily?")
        task_time = st.time_input("Scheduled time", value=None)

    if st.button("Add Task"):
        from datetime import datetime, date
        time_slot = None
        if task_time:
            today = date.today()
            time_slot = datetime.combine(today, task_time)
        task = Task(
            name=task_name,
            task_type=task_type,
            duration=duration,
            priority=priority,
            recurring=recurring,
            pet_name=selected_pet,
            time_slot=time_slot,
            due_date=date.today(),
        )
        for p in pets:
            if p.name == selected_pet:
                p.add_task(task)
                st.success(f"Added '{task_name}' for {selected_pet}!")
                st.session_state.owner.save_to_json("data.json")
                break

    # Show tasks per pet
    for p in pets:
        tasks = p.get_tasks()
        if tasks:
            st.write(f"**{p.name}'s tasks ({len(tasks)}):**")
            for t in tasks:
                status = "✅" if t.completed else "⬜"
                st.write(f"  {status} {t.name} ({t.task_type}, {t.duration}min, priority {t.priority})")

st.divider()

# Find next available slot
st.subheader("🔍 Find Next Available Slot")
slot_duration = st.number_input("Task duration (minutes)", min_value=5, max_value=240, value=30, key="slot_duration")
if st.button("Find Slot"):
    if st.session_state.scheduler is None:
        st.error("Generate a schedule first!")
    else:
        next_slot = st.session_state.scheduler.find_next_available_slot(slot_duration)
        if next_slot:
            st.success(f"✅ Next available slot: {next_slot.strftime('%H:%M')} for {slot_duration} minutes")
        else:
            st.error("❌ No available slot found for that duration today.")

# --- Generate Schedule ---
st.subheader("📅 Generate Daily Schedule")

col1, col2 = st.columns(2)
with col1:
    sort_option = st.radio("Sort tasks by:", ["Priority (highest first)", "Time (earliest first)"])
with col2:
    filter_pet = st.selectbox("Filter by pet:", ["All Pets"] + [p.name for p in pets])

if st.button("Generate Schedule"):
    scheduler = Scheduler(owner=st.session_state.owner)
    scheduler.generate_plan()
    st.session_state.scheduler = scheduler

    # Apply sorting
    if sort_option == "Time (earliest first)":
        scheduler.sort_by_time()
    else:
        scheduler.sort_by_priority()

    # Apply filtering
    if filter_pet != "All Pets":
        filtered_tasks = scheduler.filter_tasks(pet_name=filter_pet)
    else:
        filtered_tasks = scheduler.tasks

    # Show schedule as a table
    if filtered_tasks:
        st.success(f"✅ Schedule generated! {len(filtered_tasks)} tasks planned.")
        table_data = []
        for t in filtered_tasks:
            time_str = t.time_slot.strftime("%H:%M") if t.time_slot else "Unscheduled"
            if t.priority >= 4:
                priority_label = "🔴 High"
            elif t.priority >= 2:
                priority_label = "🟡 Medium"
            else:
                priority_label = "🟢 Low"
            
            type_emojis = {
                "walk": "🚶 Walk",
                "feeding": "🍽️ Feeding",
                "meds": "💊 Meds",
                "grooming": "✂️ Grooming",
                "enrichment": "🎾 Enrichment",
                "other": "📌 Other",
            }
            task_type_display = type_emojis.get(t.task_type, t.task_type)

            table_data.append({
                "Time": time_str,
                "Task": t.name,
                "Pet": t.pet_name,
                "Type": task_type_display,
                "Duration": f"{t.duration} min",
                "Priority": priority_label,
                "Recurring": "🔁" if t.recurring else "—",
            })
        st.table(table_data)
    else:
        st.info("No tasks to schedule.")

    # Conflict warnings
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        st.warning(f"⚠️ {len(conflicts)} task conflict(s) detected!")
        for c in conflicts:
            time_str = c.time_slot.strftime("%H:%M") if c.time_slot else "No time"
            st.error(f"🔴 Conflict: {c.name} for {c.pet_name} at {time_str}")
    else:
        st.success("✅ No scheduling conflicts detected!")

    # Show explanation
    with st.expander("📝 Schedule Explanation"):
        st.text(scheduler.explain_plan())

    # Show total time usage
    total_time = sum(t.duration for t in filtered_tasks)
    available = st.session_state.owner.available_time
    st.progress(min(total_time / available, 1.0))
    st.caption(f"Time used: {total_time} / {available} minutes")

st.divider()

# --- AI Care Plan (RAG-powered) ---
st.subheader("🤖 AI Care Plan (powered by RAG)")
st.caption(
    "Get a personalized daily care plan generated by AI, grounded in a "
    "knowledge base of pet care guidelines."
)

extra_context = st.text_area(
    "Anything else the AI should know? (optional)",
    placeholder="e.g., Mochi has been limping today, I'm working from home, vet visit at 3pm...",
    height=80,
)

if st.button("✨ Generate AI Care Plan"):
    if not pets:
        st.warning("Add at least one pet before generating an AI plan.")
    else:
        # Build the context string from current owner/pets/tasks
        context_lines = [
            f"Owner: {st.session_state.owner.name}",
            f"Available time today: {st.session_state.owner.available_time} minutes",
            f"Number of pets: {len(pets)}",
            "",
            "Pets and their tasks:",
        ]
        for p in pets:
            context_lines.append(
                f"- {p.name}: {p.species}, age {p.age}"
                + (f", special needs: {p.special_needs}" if p.special_needs else "")
            )
            tasks_list = p.get_tasks()
            if tasks_list:
                for t in tasks_list:
                    status = "completed" if t.completed else "pending"
                    context_lines.append(
                        f"    • {t.name} ({t.task_type}, {t.duration}min, "
                        f"priority {t.priority}, {status})"
                    )
            else:
                context_lines.append("    • No tasks yet")

        if extra_context.strip():
            context_lines.append("")
            context_lines.append(f"Additional notes: {extra_context.strip()}")

        user_context = "\n".join(context_lines)

        # Show what we're sending (transparency)
        with st.expander("🔍 Context sent to the AI"):
            st.code(user_context)

        # Call the RAG pipeline
        with st.spinner("AI is thinking..."):
            result = generate_care_plan(user_context)

        # Display the response
        if result["response"].startswith("ERROR"):
            st.error(result["response"])
        else:
            st.markdown("### 🐾 Your AI-Generated Care Plan")
            st.markdown(result["response"])

            # Hide RAG sources & confidence in a collapsible section
            with st.expander("🔍 AI transparency details (sources & confidence)"):
                st.markdown("**📚 Knowledge base sources used:**")
                for src in result["sources"]:
                    st.markdown(f"- `{src}.md`")

                confidence = result["confidence"]
                confidence_colors = {
                    "high": "🟢",
                    "medium": "🟡",
                    "low": "🔴",
                    "unknown": "⚪",
                    "none": "⚫",
                }
                icon = confidence_colors.get(confidence, "⚪")
                st.markdown(f"**{icon} AI Confidence:** {confidence}")
