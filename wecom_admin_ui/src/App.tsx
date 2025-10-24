import { Layout, Menu } from 'antd'
import { AppstoreOutlined, PlusCircleOutlined, FileSearchOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { Link, Routes, Route, useLocation } from 'react-router-dom'
import TasksList from './pages/TasksList'
import CreateTask from './pages/CreateTask'
import TaskDetail from './pages/TaskDetail'
import HealthPage from './pages/Health'
import { TeamOutlined } from '@ant-design/icons'
import MembersList from './pages/MembersList'
import MemberDetail from './pages/MemberDetail'
import { FilterOutlined } from '@ant-design/icons'
import Planning from './pages/Planning'

const { Header, Sider, Content } = Layout
export default function App(){
  const { pathname } = useLocation()
  const selected =
    pathname.startsWith('/tasks/create') ? ['create']
    : pathname.startsWith('/tasks/') ? ['detail']
    : pathname.startsWith('/health') ? ['health']
    : ['list']
  
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="light" width={220}>
        <div style={{ padding: 12, fontWeight: 700 }}>WeCom Ops Admin</div>
        <Menu mode="inline" selectedKeys={selected}
          items={[
            { key:'list', icon:<AppstoreOutlined/>, label:<Link to="/tasks">任务列表</Link> },
            { key:'create', icon:<PlusCircleOutlined/>, label:<Link to="/tasks/create">创建任务</Link> },
            { key:'detail', icon:<FileSearchOutlined/>, label:<Link to="/tasks/1">任务详情(示例)</Link> },
            { key:'health', icon:<SafetyCertificateOutlined/>, label:<Link to="/health">健康检查</Link> },
            { key: '/members', icon: <TeamOutlined />, label: <Link to="/members">会员中心</Link> },
            { key: '/planning', icon: <FilterOutlined />, label: <Link to="/planning">规划能力</Link> },
          ]}
        />
      </Sider>
      <Layout>
        <Header style={{ background:'#fff', padding:'0 16px', fontWeight:600 }}>企业微信群发 · 管理后台</Header>
        <Content style={{ margin:16, background:'#fff', padding:16 }}>
          <Routes>
            <Route path="/" element={<TasksList/>} />
            <Route path="/tasks" element={<TasksList/>} />
            <Route path="/tasks/create" element={<CreateTask/>} />
            <Route path="/tasks/:id" element={<TaskDetail/>} />
            <Route path="/health" element={<HealthPage/>} /> {/* 已添加健康检查路由 */}
            <Route path="/members" element={<MembersList />} />
            <Route path="/members/:id" element={<MemberDetail />} />
            <Route path="/planning" element={<Planning />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}