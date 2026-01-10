import { useState } from "react";
import { motion } from "framer-motion";
import { AppHeader } from "@/components/layout/AppHeader";
import { DeviceCard } from "@/components/devices/DeviceCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Search, Filter } from "lucide-react";
import { useDevicesData } from "@/data/mockDataHooks";
import { useNavigate } from "react-router-dom";

const DevicesPage = () => {
  const navigate = useNavigate();
  const devices = useDevicesData();
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filteredDevices = devices.filter((device) => {
    const matchesSearch = device.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      device.serialNumber.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = typeFilter === "all" || device.type === typeFilter;
    const matchesStatus = statusFilter === "all" || device.status === statusFilter;
    return matchesSearch && matchesType && matchesStatus;
  });

  const handleConfigure = (deviceId: string) => {
    navigate(`/start/devices/${deviceId}/settings`);
  };

  const handleViewTelemetry = (deviceId: string) => {
    navigate(`/start/telemetry?device=${deviceId}`);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader 
        title="Devices" 
        subtitle="Manage your solar installation equipment"
      />
      
      <div className="p-3 sm:p-6 space-y-4 sm:space-y-6">
        {/* Filters */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-3 sm:p-4"
        >
          <div className="flex flex-col gap-4">
            {/* Search */}
            <div className="relative w-full">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by name or serial..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-secondary/50"
              />
            </div>
            
            {/* Filter Row */}
            <div className="flex flex-wrap gap-2">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-full sm:w-[130px] bg-secondary/50">
                  <Filter className="w-4 h-4 mr-2 flex-shrink-0" />
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="inverter">Inverters</SelectItem>
                  <SelectItem value="battery">Batteries</SelectItem>
                  <SelectItem value="meter">Meters</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-[130px] bg-secondary/50">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="online">Online</SelectItem>
                  <SelectItem value="offline">Offline</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                </SelectContent>
              </Select>

              <Button className="w-full sm:w-auto gap-2" onClick={() => navigate("/start/devices/manage")}>
                <Plus className="w-4 h-4" />
                <span className="sm:inline">Add Device</span>
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Device Count */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Showing {filteredDevices.length} of {devices.length} devices</span>
        </div>

        {/* Device Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-6">
          {filteredDevices.map((device, index) => (
            <DeviceCard
              key={device.id}
              {...device}
              delay={index * 0.1}
              onConfigure={() => handleConfigure(device.id)}
              onViewTelemetry={() => handleViewTelemetry(device.id)}
            />
          ))}
        </div>

        {filteredDevices.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-12"
          >
            <p className="text-muted-foreground">No devices found matching your criteria.</p>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default DevicesPage;
