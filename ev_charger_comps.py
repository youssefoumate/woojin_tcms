import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- Diagram Components ---
def draw_component(ax, x, y, width, height, label, color='#e0f7fa'):
    """Draws a rectangular component with a label."""
    rect = patches.Rectangle((x, y), width, height, facecolor=color, edgecolor='black', linewidth=1)
    ax.add_patch(rect)
    ax.text(x + width / 2, y + height / 2, label, ha='center', va='center', fontsize=10)

def draw_arrow(ax, start_x, start_y, end_x, end_y, label=None):
    """Draws an arrow between two points, optionally with a label."""
    ax.arrow(start_x, start_y, end_x - start_x, end_y - start_y,
             head_width=0.15, head_length=0.2, fc='black', ec='black', linewidth=1,
             length_includes_head=True)
    if label:
        ax.text((start_x + end_x) / 2, (start_y + end_y) / 2 + 0.2, label, ha='center', va='bottom', fontsize=8)

# --- Set up the plot ---
fig, ax = plt.subplots(figsize=(12, 8))
ax.set_aspect('equal') # Ensure circular shapes are not distorted
ax.axis('off') # Hide axes

# --- Component Positions and Sizes (Adjust as needed) ---
x_start = 1
y_start = 1

component_width = 2
component_height = 1.5
x_spacing = 3  # Horizontal spacing between components
y_spacing = 2  # Vertical spacing (not really used much here, mostly horizontal flow)

# --- 1. Grid Connection ---
grid_x = x_start
grid_y = y_start + y_spacing * 3
draw_component(ax, grid_x, grid_y, component_width, component_height, "Grid\nConnection", '#c8e6c9')

# --- 2. Input Filter & EMC ---
filter_x = grid_x + x_spacing
filter_y = grid_y
draw_component(ax, filter_x, filter_y, component_width, component_height, "Input Filter &\nEMC", '#c8e6c9')
draw_arrow(ax, grid_x + component_width, grid_y + component_height/2, filter_x, grid_y + component_height/2)

# --- 3. Rectifier (AC-DC) ---
rectifier_x = filter_x + x_spacing
rectifier_y = grid_y
draw_component(ax, rectifier_x, rectifier_y, component_width, component_height, "Rectifier\n(AC to DC)", '#ffcc80')
draw_arrow(ax, filter_x + component_width, filter_y + component_height/2, rectifier_x, filter_y + component_height/2)

# --- 4. Power Factor Correction (PFC) - Optional but Common ---
pfc_x = rectifier_x + x_spacing
pfc_y = grid_y
draw_component(ax, pfc_x, pfc_y, component_width, component_height, "PFC\n(Optional)", '#ffcc80')
draw_arrow(ax, rectifier_x + component_width, rectifier_y + component_height/2, pfc_x, rectifier_y + component_height/2)

# --- 5. DC-DC Converter (Isolation & Voltage Adjustment) ---
dc_dc_x = pfc_x + x_spacing
dc_dc_y = grid_y
draw_component(ax, dc_dc_x, dc_dc_y, component_width, component_height, "DC-DC\nConverter", '#ffcc80')
draw_arrow(ax, pfc_x + component_width, pfc_y + component_height/2, dc_dc_x, pfc_y + component_height/2)

# --- 6. Charging Controller & Communication ---
controller_x = dc_dc_x + x_spacing
controller_y = grid_y + y_spacing/2  # Slightly lower for visual flow
draw_component(ax, controller_x, controller_y, component_width, component_height * 2, "Charging\nController &\nCommunication", '#b3e0ff')
draw_arrow(ax, dc_dc_x + component_width, dc_dc_y + component_height/2, controller_x, controller_y + component_height/2)

# --- 7. User Interface (UI) ---
ui_x = controller_x + x_spacing
ui_y = controller_y + component_height/2
draw_component(ax, ui_x, ui_y, component_width, component_height, "User\nInterface (UI)", '#b3e0ff')
draw_arrow(ax, controller_x + component_width, controller_y + component_height, ui_x, ui_y + component_height)

# --- 8. Safety & Protection Circuits ---
safety_x = controller_x + x_spacing
safety_y = controller_y - component_height/2
draw_component(ax, safety_x, safety_y, component_width, component_height, "Safety &\nProtection", '#b3e0ff')
draw_arrow(ax, controller_x + component_width, controller_y, safety_x, safety_y)


# --- 9. EV Connector & Cable ---
connector_x = ui_x + x_spacing + 1 # Spacing a bit more for the connector
connector_y = controller_y
draw_component(ax, connector_x, connector_y, component_width, component_height, "EV\nConnector &\nCable", '#ffab91')
draw_arrow(ax, ui_x + component_width, ui_y + component_height/2, connector_x, connector_y + component_height/2)
draw_arrow(ax, safety_x + component_width, safety_y + component_height/2, connector_x, connector_y - component_height/2)
draw_arrow(ax, controller_x + component_width/2, controller_y - component_height, connector_x - component_width/2, connector_y - component_height * 1.5, label="Control &\nCommunication") # Control/Comm arrow

# --- 10. Electric Vehicle Battery ---
ev_battery_x = connector_x + x_spacing
ev_battery_y = controller_y
draw_component(ax, ev_battery_x, ev_battery_y, component_width, component_height, "EV\nBattery", '#ffab91')
draw_arrow(ax, connector_x + component_width, connector_y + component_height/2, ev_battery_x, ev_battery_y + component_height/2)


# --- Title and Description ---
plt.title('Components of an EV Charger', fontsize=14, pad=20)
plt.text(x_start, y_start - 1,
         "This diagram illustrates the key components of a typical Electric Vehicle (EV) charger.\n"
         "The energy flows from the grid, is conditioned and converted by various components, \n"
         "controlled by the charging controller, and finally delivered to the EV battery.\n"
         "User interface and safety features ensure proper and safe operation.",
         fontsize=9, ha='left', va='top', wrap=True, bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=10))


plt.xlim(x_start - 1, ev_battery_x + component_width + 2) # Adjust x limits for better view
plt.ylim(y_start - 2, grid_y + component_height + 2)      # Adjust y limits

plt.show()


