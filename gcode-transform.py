#!/usr/bin/env python3
# gcode-transform: transform G-Code coordinates
# Copyright(c) 2025 by egroshev "Erik Groshev" <erikgroshev@gmail.com>
# Distributed under the GNU GPLv3+ license, WITHOUT ANY WARRANTY.
import argparse
import re
import sys
import numpy as np
import math
import os

# --- Configuration and Helpers ---

def coord_pair(string):
    """Custom type to parse 'XxY' string into a list of two floats."""
    try:
        x, y = map(float, string.split('x'))
        return [x, y]
    except ValueError:
        raise argparse.ArgumentTypeError("Center must be in 'XxY' format (e.g., '125x100').")

def transform_gcode(input_path, rotate_deg, shift_x, shift_y, center_str, precision):
    """Applies rotation and translation to G-code coordinates using NumPy matrices."""
    
    # --- 1. Setup Transformation Parameters ---
    
    # Parse the center point string
    center = coord_pair(center_str)

    # SHIFT LOGIC: Direct interpretation (e.g., shiftx=5 means X=+5, shiftx=-5 means X=-5)
    translate_x = shift_x
    translate_y = shift_y
    
    is_rotation_requested = (rotate_deg != 0.0)
    is_shift_requested = (shift_x != 0.0 or shift_y != 0.0)

    # If no transformation is requested
    if not is_rotation_requested and not is_shift_requested:
        print(f"Warning: No rotation or shift requested. File will be copied.", file=sys.stderr)

    # --- 2. Setup Homogeneous Transformation Matrices ---
    
    if is_rotation_requested:
        # ROTATION LOGIC: Positive angle results in CW rotation, matching the user's matrix convention.
        angle = np.radians(rotate_deg)
        
        # This matrix performs a CW rotation for positive 'angle'
        R = np.array([[ np.cos(angle), np.sin(angle), 0],
                      [-np.sin(angle), np.cos(angle), 0],
                      [0, 0, 1]])
        rT = np.array([[1, 0, center[0]], [0, 1, center[1]], [0, 0, 1]])
        rT_inv = np.linalg.inv(rT)
    else:
        # Identity matrices if no rotation is needed
        R = np.identity(3)
        rT = np.identity(3)
        rT_inv = np.identity(3)

    # mT: Translation matrix for the final X/Y shift
    mT = np.array([[1, 0, translate_x],
                   [0, 1, translate_y],
                   [0, 0, 1]])
                   
    # A: Combined Homogeneous Transformation Matrix (Rotation @ Translation)
    A = mT @ rT @ R @ rT_inv

    # Format string for coordinate output precision
    fmt_str = '{{:.{}f}}'.format(precision)
    def format_coord(x):
        return fmt_str.format(x)

    # --- 3. G-Code State Tracking ---
    pos = [0.0, 0.0] # Current absolute position [X, Y]
    rel = None # G91 (Relative mode) = True, G90 (Absolute mode) = False
    
    # --- 4. G-Code Processing ---
    modified_lines = []
    
    try:
        fd = sys.stdin if input_path is None else open(input_path)
        
        # Add header to the output
        modified_lines.append(f"; G-code file modified by gcode-transform.py")
        modified_lines.append(f"; Original: {input_path}")
        modified_lines.append(f"; Center: {center_str}, Rotation: {rotate_deg}°")
        modified_lines.append(f"; Translation: X={translate_x:.3f}mm, Y={translate_y:.3f}mm\n")

        for line in fd:
            original_line = line.rstrip('\n')
            clean_line, *comment = original_line.split(';', 1)
            clean_line = clean_line.strip()
            
            if not clean_line:
                modified_lines.append(original_line)
                continue
            
            # Handle Absolute/Relative Mode Switching (G90/G91)
            if re.match(r'G90\b', clean_line):
                rel = False
                modified_lines.append(original_line)
                continue
            if re.match(r'G91\b', clean_line):
                rel = True
                modified_lines.append(original_line)
                continue
            
            # Skip non-motion commands
            if not re.match(r'[Gg][01]\b', clean_line):
                modified_lines.append(original_line)
                continue

            # Parse X/Y coordinates
            coords_delta = [None, None]
            seen_xy = False
            
            for i, p in enumerate(['X', 'Y']):
                m = re.search(r' {}(\S+)'.format(p), clean_line)
                if m is not None:
                    val = float(m.group(1))
                    seen_xy = True
                    coords_delta[i] = val
                    
            if not seen_xy or (not is_rotation_requested and not is_shift_requested):
                modified_lines.append(original_line)
                continue
                
            # Calculate the TRUE absolute position of the destination (Pre-transform)
            current_pos_x, current_pos_y = pos[0], pos[1]
            
            if rel: # G91
                dest_x = current_pos_x + (coords_delta[0] if coords_delta[0] is not None else 0.0)
                dest_y = current_pos_y + (coords_delta[1] if coords_delta[1] is not None else 0.0)
            else: # G90
                dest_x = coords_delta[0] if coords_delta[0] is not None else current_pos_x
                dest_y = coords_delta[1] if coords_delta[1] is not None else current_pos_y

            # Apply Homogeneous Transformation
            
            # Transform the current (previous) position
            V_prev = np.array([current_pos_x, current_pos_y, 1])
            V_prev_t = A @ V_prev
            current_pos_x_t, current_pos_y_t = V_prev_t[0], V_prev_t[1]

            # Transform the destination position
            V_dest = np.array([dest_x, dest_y, 1])
            V_dest_t = A @ V_dest
            dest_x_t, dest_y_t = V_dest_t[0], V_dest_t[1]

            # Prepare the final G-code line
            new_x_str, new_y_str = None, None
            
            if rel: # G91
                # Update absolute position tracker
                pos[0], pos[1] = dest_x_t, dest_y_t
                
                # Calculate new deltas
                if coords_delta[0] is not None:
                    delta_x = dest_x_t - current_pos_x_t
                    new_x_str = f'X{format_coord(delta_x)}'
                
                if coords_delta[1] is not None:
                    delta_y = dest_y_t - current_pos_y_t
                    new_y_str = f'Y{format_coord(delta_y)}'
                    
            else: # G90
                # Update absolute position tracker
                pos[0], pos[1] = dest_x_t, dest_y_t
                
                # Use the new transformed absolute position
                if coords_delta[0] is not None:
                    new_x_str = f'X{format_coord(dest_x_t)}'
                
                if coords_delta[1] is not None:
                    new_y_str = f'Y{format_coord(dest_y_t)}'
            
            
            # Reconstruct the line: 
            new_line = re.sub(r' [XY]\S+', '', clean_line) # Remove old X/Y
            
            if new_x_str:
                new_line = new_line + ' ' + new_x_str
            if new_y_str:
                new_line = new_line + ' ' + new_y_str
            
            # Add back comments
            if comment:
                new_line = f"{new_line} ;{comment[0]}"
            
            modified_lines.append(new_line.strip())
            
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except ValueError as ve:
        print(f"Error: {ve}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}", file=sys.stderr)
        sys.exit(1)

    # --- 5. Print to Standard Output ---
    for line in modified_lines:
        print(line)


def main():
    parser = argparse.ArgumentParser(
        description="Rotates and shifts G-code coordinates using robust matrix transformation.",
        epilog="Example: python3 gcode-transform.py --rotate 4 --shiftx -5 gcodes/Koru_42_R.gcode > transformed.gcode\n"
               "Interpretation: Positive rotate=CW, Negative rotate=CCW. Positive shiftx=Right, Negative shiftx=Left."
    )
    
    # Arguments are optional and default to 0.0
    parser.add_argument('--rotate', type=float, default=0.0, 
                        help="Angle in degrees (Positive=CW, Negative=CCW).")
    parser.add_argument('--shiftx', type=float, default=0.0, 
                        help="Shift distance for X-axis (Positive=Right, Negative=Left).")
    parser.add_argument('--shifty', type=float, default=0.0, 
                        help="Shift distance for Y-axis (Positive=Forward, Negative=Backward).")
    
    # Center is optional, defaulting to 125x100
    parser.add_argument('--center', type=str, default="125x100", 
                        help="XxY rotation center (mm, e.g., '125x100'). Defaults to 125x100.")
    parser.add_argument('--precision', type=int, default=3,
                        help="Output coordinate decimal precision (default: 3).")
    
    # The input file is required (positional argument)
    parser.add_argument('input_file', type=str, help="Path to the input G-code file.")
    
    args = parser.parse_args()
    
    # Check for numpy
    try:
        import numpy as np
    except ImportError:
        print("\nError: The 'numpy' library is required for this script.", file=sys.stderr)
        print("Please install it using: pip install numpy\n", file=sys.stderr)
        sys.exit(1)
        
    transform_gcode(args.input_file, args.rotate, args.shiftx, args.shifty, args.center, args.precision)

if __name__ == "__main__":
    main()
