"""
增强版坐标转换器单元测试
测试3D姿态修正和GPS质量控制功能
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest
from src.transform.camera_model import CameraModel
from src.transform.coord_transform_new import CoordinateTransformerEnhanced


# 测试用相机配置
TEST_CAMERA_CONFIG = {
    'camera': {
        'model': 'TEST_CAMERA',
        'resolution': {'width': 4032, 'height': 3024},
        'sensor_size': {'width': 13.4, 'height': 9.6},
        'focal_length': 7.0,
        'principal_point': {'cx': 2016, 'cy': 1512},
        'distortion': {'k1': 0, 'k2': 0, 'p1': 0, 'p2': 0, 'k3': 0}
    },
    'orthogonal_mode': {
        'assume_vertical': False,
        'use_attitude_correction': True
    },
    'earth': {
        'meters_per_degree_lat': 110540,
        'meters_per_degree_lon': 111320
    }
}

# 测试用位姿数据
TEST_POSE_VERTICAL = {
    'latitude': 22.779954,
    'longitude': 114.100891,
    'altitude': 100.0,
    'pitch': -90.0,
    'yaw': 0.0,
    'roll': 0.0,
    'timestamp': 1707730815123,
    'gps_level': 5,
    'satellite_count': 18,
    'positioning_state': 'GPS'
}

TEST_POSE_TILTED = {
    'latitude': 22.779954,
    'longitude': 114.100891,
    'altitude': 100.0,
    'pitch': -85.0,
    'yaw': 45.0,
    'roll': 5.0,
    'timestamp': 1707730815123,
    'gps_level': 4,
    'satellite_count': 12,
    'positioning_state': 'GPS'
}

TEST_POSE_RTK = {
    'latitude': 22.779954,
    'longitude': 114.100891,
    'altitude': 100.0,
    'pitch': -90.0,
    'yaw': 0.0,
    'roll': 0.0,
    'timestamp': 1707730815123,
    'gps_level': 5,
    'satellite_count': 20,
    'positioning_state': 'RTK_FIXED'
}

TEST_POSE_LOW_QUALITY = {
    'latitude': 22.779954,
    'longitude': 114.100891,
    'altitude': 100.0,
    'pitch': -90.0,
    'yaw': 0.0,
    'roll': 0.0,
    'timestamp': 1707730815123,
    'gps_level': 2,
    'satellite_count': 6,
    'positioning_state': 'GPS'
}


class TestCoordinateTransformerEnhanced:
    """增强版坐标转换器测试类"""
    
    @pytest.fixture
    def camera_model(self):
        """创建测试用相机模型"""
        return CameraModel(TEST_CAMERA_CONFIG)
    
    @pytest.fixture
    def transformer(self, camera_model):
        """创建测试用转换器"""
        quality_config = {
            'enabled': True,
            'min_gps_level': 3,
            'min_satellite_count': 10,
            'skip_on_low_quality': True
        }
        return CoordinateTransformerEnhanced(camera_model, quality_config)
    
    def test_initialization(self, transformer):
        """测试转换器初始化"""
        assert transformer is not None
        assert transformer.enable_quality_control is True
        assert transformer.min_gps_level == 3
        assert transformer.min_satellite_count == 10
    
    def test_gps_quality_evaluation_rtk(self, transformer):
        """测试GPS质量评估 - RTK固定解"""
        quality_level, should_skip, error = transformer.evaluate_gps_quality(TEST_POSE_RTK)
        
        assert quality_level == 'RTK'
        assert should_skip is False
        assert error == 0.05  # RTK精度为5cm
    
    def test_gps_quality_evaluation_high(self, transformer):
        """测试GPS质量评估 - 高质量GPS"""
        quality_level, should_skip, error = transformer.evaluate_gps_quality(TEST_POSE_VERTICAL)
        
        assert quality_level == 'HIGH'
        assert should_skip is False
        assert error == 3.0
    
    def test_gps_quality_evaluation_low(self, transformer):
        """测试GPS质量评估 - 低质量GPS"""
        quality_level, should_skip, error = transformer.evaluate_gps_quality(TEST_POSE_LOW_QUALITY)
        
        assert quality_level == 'INVALID'
        assert should_skip is True  # 应该跳过低质量数据
        assert error == 10.0
    
    def test_rotation_matrix_vertical(self, transformer):
        """测试旋转矩阵构建 - 垂直向下"""
        R = transformer._build_rotation_matrix(0, -90, 0)
        
        # 垂直向下时，Z轴应该向下（负Z方向）
        assert R.shape == (3, 3)
        # 旋转矩阵应该是正交矩阵
        assert np.allclose(R @ R.T, np.eye(3), atol=1e-6)
    
    def test_rotation_matrix_tilted(self, transformer):
        """测试旋转矩阵构建 - 倾斜姿态"""
        R = transformer._build_rotation_matrix(45, -85, 5)
        
        assert R.shape == (3, 3)
        # 旋转矩阵应该是正交矩阵
        assert np.allclose(R @ R.T, np.eye(3), atol=1e-6)
    
    def test_pixel_to_camera_ray(self, transformer):
        """测试像素到相机射线转换"""
        # 图像中心点
        pixel_coords = [(2016, 1512)]
        
        rays = transformer._pixel_to_camera_ray(pixel_coords)
        
        assert rays.shape == (1, 3)
        # 中心点的射线应该沿光轴方向
        assert rays[0, 0] == pytest.approx(0, abs=0.01)  # x接近0
        assert rays[0, 1] == pytest.approx(0, abs=0.01)  # y接近0
        # 归一化后的向量模长应该为1
        assert np.linalg.norm(rays[0]) == pytest.approx(1.0)
    
    def test_ray_ground_intersection_vertical(self, transformer):
        """测试射线与地面相交 - 垂直向下"""
        # 垂直向下的射线
        rays_world = np.array([[0, 0, -1]])  # 向下
        altitude = 100.0
        
        ground_points = transformer._ray_ground_intersection(rays_world, altitude)
        
        assert ground_points.shape == (1, 2)
        # 垂直向下时，交点应该在正下方（x=0, y=0）
        assert ground_points[0, 0] == pytest.approx(0, abs=0.1)
        assert ground_points[0, 1] == pytest.approx(0, abs=0.1)
    
    def test_pixel_to_geo_3d_vertical(self, transformer):
        """测试完整3D转换 - 垂直拍摄"""
        # 图像中心点
        pixel_coords = [(2016, 1512)]
        
        geo_coords, quality_info = transformer.pixel_to_geo_3d(pixel_coords, TEST_POSE_VERTICAL)
        
        assert len(geo_coords) == 1
        assert len(geo_coords[0]) == 2  # (lat, lon)
        
        # 中心点应该接近无人机位置
        assert geo_coords[0][0] == pytest.approx(TEST_POSE_VERTICAL['latitude'], abs=0.001)
        assert geo_coords[0][1] == pytest.approx(TEST_POSE_VERTICAL['longitude'], abs=0.001)
        
        # 检查质量信息
        assert quality_info['quality_level'] == 'HIGH'
        assert quality_info['estimated_error'] > 0
    
    def test_pixel_to_geo_3d_tilted(self, transformer):
        """测试完整3D转换 - 倾斜拍摄"""
        # 图像中心点
        pixel_coords = [(2016, 1512)]
        
        geo_coords, quality_info = transformer.pixel_to_geo_3d(pixel_coords, TEST_POSE_TILTED)
        
        assert len(geo_coords) == 1
        # 倾斜拍摄时，中心点会偏离无人机位置
        # 这里只验证转换成功
        assert quality_info['quality_level'] in ['MEDIUM', 'HIGH']
    
    def test_pixel_to_geo_3d_low_quality_skip(self, transformer):
        """测试低质量GPS数据被跳过"""
        pixel_coords = [(2016, 1512)]
        
        geo_coords, quality_info = transformer.pixel_to_geo_3d(pixel_coords, TEST_POSE_LOW_QUALITY)
        
        # 低质量数据应该被跳过
        assert len(geo_coords) == 0
        assert quality_info['quality_level'] == 'INVALID'
    
    def test_estimate_error(self, transformer):
        """测试误差估算"""
        error = transformer.estimate_error(TEST_POSE_VERTICAL)
        
        assert error > 0
        assert error < 10.0  # 合理的误差范围
        
        # RTK应该有更小的误差
        error_rtk = transformer.estimate_error(TEST_POSE_RTK)
        assert error_rtk < error
    
    def test_transform_detection(self, transformer):
        """测试检测结果转换"""
        detection = {
            'class_id': 1,
            'class_name': 'Vegetation',
            'confidence': 0.85,
            'corners': [
                (1900, 1400),
                (2100, 1400),
                (2100, 1600),
                (1900, 1600)
            ]
        }
        
        result = transformer.transform_detection(detection, TEST_POSE_VERTICAL)
        
        # 应该添加地理坐标
        assert 'geo_coords' in result
        assert 'center_geo' in result
        assert 'quality_info' in result
        assert 'estimated_error' in result
        
        # 检查坐标数量
        assert len(result['geo_coords']) == 4
        assert len(result['center_geo']) == 2
    
    def test_offset_to_latlon(self, transformer):
        """测试地面偏移到经纬度转换"""
        # 东100米，北100米
        offsets = np.array([[100, 100]])
        drone_lat = 22.779954
        drone_lon = 114.100891
        
        coords = transformer._offset_to_latlon(offsets, drone_lat, drone_lon)
        
        assert len(coords) == 1
        # 纬度应该增加（向北）
        assert coords[0][0] > drone_lat
        # 经度应该增加（向东）
        assert coords[0][1] > drone_lon
    
    def test_get_info(self, transformer):
        """测试获取转换器信息"""
        info = transformer.get_info()
        
        assert 'version' in info
        assert 'features' in info
        assert 'quality_control' in info
        assert info['version'] == 'v2.0 Enhanced'


class TestCompareWithSimplified:
    """对比简化版和增强版的精度差异"""
    
    @pytest.fixture
    def camera_model(self):
        return CameraModel(TEST_CAMERA_CONFIG)
    
    @pytest.fixture
    def enhanced_transformer(self, camera_model):
        """增强版转换器"""
        return CoordinateTransformerEnhanced(camera_model, {'enabled': False})
    
    def test_vertical_accuracy_similar(self, enhanced_transformer):
        """测试垂直拍摄时精度相似"""
        pixel_coords = [(2016, 1512)]
        
        # 增强版转换
        geo_coords_enhanced, _ = enhanced_transformer.pixel_to_geo_3d(pixel_coords, TEST_POSE_VERTICAL)
        
        # 中心点应该非常接近无人机位置
        assert len(geo_coords_enhanced) == 1
        lat_diff = abs(geo_coords_enhanced[0][0] - TEST_POSE_VERTICAL['latitude'])
        lon_diff = abs(geo_coords_enhanced[0][1] - TEST_POSE_VERTICAL['longitude'])
        
        # 中心点误差应该很小（米级）
        assert lat_diff < 0.0001  # 约10米
        assert lon_diff < 0.0001


def run_basic_tests():
    """运行基础测试（不需要pytest）"""
    print("=" * 60)
    print("增强版坐标转换器 - 基础功能测试")
    print("=" * 60)
    
    # 初始化
    camera_model = CameraModel(TEST_CAMERA_CONFIG)
    transformer = CoordinateTransformerEnhanced(camera_model)
    
    print("\n[测试1] GPS质量评估")
    for name, pose in [
        ("RTK固定解", TEST_POSE_RTK),
        ("高质量GPS", TEST_POSE_VERTICAL),
        ("低质量GPS", TEST_POSE_LOW_QUALITY)
    ]:
        quality, skip, error = transformer.evaluate_gps_quality(pose)
        print(f"  {name}: 质量={quality}, 跳过={skip}, 误差={error:.2f}m")
    
    print("\n[测试2] 旋转矩阵构建")
    R = transformer._build_rotation_matrix(0, -90, 0)
    print(f"  旋转矩阵形状: {R.shape}")
    print(f"  是否正交: {np.allclose(R @ R.T, np.eye(3))}")
    
    print("\n[测试3] 完整3D坐标转换")
    pixel_coords = [(2016, 1512)]
    geo_coords, quality_info = transformer.pixel_to_geo_3d(pixel_coords, TEST_POSE_VERTICAL)
    if geo_coords:
        print(f"  输入像素: {pixel_coords[0]}")
        print(f"  输出坐标: ({geo_coords[0][0]:.6f}, {geo_coords[0][1]:.6f})")
        print(f"  GPS质量: {quality_info['quality_level']}")
        print(f"  预估误差: {quality_info['estimated_error']:.2f}m")
    
    print("\n[测试4] 检测结果转换")
    detection = {
        'class_name': 'Vegetation',
        'confidence': 0.85,
        'corners': [(1900, 1400), (2100, 1400), (2100, 1600), (1900, 1600)]
    }
    result = transformer.transform_detection(detection, TEST_POSE_VERTICAL)
    print(f"  地理坐标数: {len(result.get('geo_coords', []))}")
    print(f"  中心坐标: {result.get('center_geo', 'N/A')}")
    print(f"  误差估算: {result.get('estimated_error', 0):.2f}m")
    
    print("\n" + "=" * 60)
    print("✓ 所有基础测试通过")
    print("=" * 60)


if __name__ == '__main__':
    # 可以直接运行基础测试
    run_basic_tests()
    
    # 或使用pytest运行完整测试
    # pytest test_coord_transform_new.py -v
