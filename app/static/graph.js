function renderGraph(data) {
    const width = document.getElementById("graph").clientWidth;
    const height = 500;

    const svg = d3.select("#graph")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    const simulation = d3.forceSimulation(data.nodes)
        .force("link", d3.forceLink(data.links).id(d => d.id).distance(160))
        .force("charge", d3.forceManyBody().strength(-500))
        .force("center", d3.forceCenter(width / 2, height / 2));

    const linkMap = new Map();
    data.links.forEach(link => {
        if (!linkMap.has(link.target)) linkMap.set(link.target, []);
        linkMap.get(link.target).push(link);
    });

    // Функция определения состояния узла
    function getNodeStatus(node) {
        if (node.completed) return 'done';

        const requiredIds = node.requires || linkMap.get(node.id)?.map(l => l.source) || [];

        const isAvailable = requiredIds.every(reqId => {
            const reqNode = data.nodes.find(n => n.id === reqId);
            return reqNode?.completed;
        });

        return isAvailable ? 'available' : 'locked';
    }

    const link = svg.append("g")
        .selectAll("line")
        .data(data.links)
        .enter().append("line")
        .attr("stroke", d => d.main ? "#bbb" : "#ccc")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", d => d.main ? "0" : "4,3");

    const node = svg.append("g")
        .selectAll("circle")
        .data(data.nodes)
        .enter().append("circle")
        .attr("r", 38)
        .attr("fill", function (d) {
            const status = getNodeStatus(d);
            const isMain = data.links.find(l => l.target === d.id)?.main;

            if (isMain) {
                if (status === 'done') return "#4CAF50";          // зелёный
                if (status === 'available') return "#2196F3";     // синий
                return "#555";                                    // тёмно-серый
            } else {
                if (status === 'done') return "#A5D6A7";          // светло-зелёный
                if (status === 'available') return "#AB47BC";     // фиолетовый
                return "#ccc";                                    // светло-серый
            }
        })
        .attr("stroke", "#444")
        .attr("stroke-width", 2)
        .style("cursor", "pointer")
        .on("click", showNodeInfo)
        .call(d3.drag()
            .on("start", dragStart)
            .on("drag", dragged)
            .on("end", dragEnd));

    const label = svg.append("g")
        .selectAll("text")
        .data(data.nodes)
        .enter().append("text")
        .attr("text-anchor", "middle")
        .attr("dy", ".35em")
        .style("font-size", "13px")
        .style("pointer-events", "none")
        .text(d => d.name);

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        label
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    });

    function dragStart(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragEnd(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    function showNodeInfo(event, node) {
        const infoBox = document.getElementById("graph-info");
        const status = getNodeStatus(node);
        let html = `<h3>${node.name}</h3>`;

        if (status === 'done') {
            html += `<p>✅ Пройдено</p>`;
        } else if (status === 'available') {
            html += `<p>🔓 Этап доступен</p>`;
            html += `<button class="btn-secondary" onclick="alert('Переход к занятию: ${node.name}')">Приступить к занятию</button>`;
        } else {
            const requiredNames = (node.requires || linkMap.get(node.id)?.map(l => l.source) || [])
                .map(id => data.nodes.find(n => n.id === id)?.name || "неизвестно");
            html += `<p>🔒 Этап недоступен</p>`;
            html += `<p>Необходимо завершить: ${requiredNames.join(', ')}</p>`;
        }

        infoBox.innerHTML = html;
        infoBox.style.display = 'block';
    }
}
