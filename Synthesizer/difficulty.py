# 定义不同难度的配置
difficulty_ranges = {
    "easy": {
        "order": "small",
        "split_arrow": (0, 0),
        "merge_arrow": (0, 0),
        "branch": (2, 3),
        "nest": 0,
        "density": (1.0, 1.1),
        "no_edge_label": (0.3, 0.6),
    },
    "medium": {
        "order": "medium",
        "split_arrow": (1, 2),
        "merge_arrow": (1, 2),
        "branch": (2, 3),
        "nest": 1,
        "density": (1.1, 1.2),
        "no_edge_label": (0.6, 0.8),
    },
    "hard": {
        "order": "large",
        "split_arrow": (2, 3),
        "merge_arrow": (2, 3),
        "branch": (3, 4),
        "nest": 2,
        "density": (1.2, 1.3),
        "no_edge_label": (0.8, 1.0),
    }
}

# 扫描风格的不同难度配置
scanned_style_difficulty = {
    "easy": {
        "enable": True,
        "blur_radius": 0.8,
        "vignette": 0.1,
        "rotation": 1.0,
        "perspective_distortion": False,
        "color_tint": "yellowish",
        "noise_level": 0.005,
        "compression_level": 90
    },
    "medium": {
        "enable": True,
        "blur_radius": 1.0,
        "vignette": 0.3,
        "rotation": 1.2,
        "perspective_distortion": False,
        "color_tint": "yellowish",
        "noise_level": 0.008,
        "compression_level": 70
    },
    "hard": {
        "enable": True,
        "blur_radius": 1.2,
        "vignette": 0.5,
        "rotation": 1.5,
        "perspective_distortion": True,
        "color_tint": "gray",
        "noise_level": 0.015,
        "compression_level": 40
    }
}
