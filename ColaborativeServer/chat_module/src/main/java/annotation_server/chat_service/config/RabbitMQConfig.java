package annotation_server.chat_service.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.ExchangeBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    @Value("${rabbitmq.exchange.auth-events:auth.events}")
    private String authEventsExchange;

    @Value("${rabbitmq.queue.user-register:chat.user.register.queue}")
    private String userRegisterQueue;

    @Value("${rabbitmq.routing-key.user-register:auth.user.register}")
    private String userRegisterRoutingKey;

    @Bean
    public TopicExchange authEventsExchange() {
        return ExchangeBuilder.topicExchange(authEventsExchange).durable(true).build();
    }

    @Bean
    public Queue userRegisterQueue() {
        return new Queue(userRegisterQueue, true);
    }

    @Bean
    public Binding userRegisterBinding(Queue userRegisterQueue, TopicExchange authEventsExchange) {
        return BindingBuilder.bind(userRegisterQueue).to(authEventsExchange).with(userRegisterRoutingKey);
    }

    @Bean
    public MessageConverter jsonMessageConverter(ObjectMapper objectMapper) {
        return new Jackson2JsonMessageConverter(objectMapper);
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory, MessageConverter jsonMessageConverter) {
        RabbitTemplate rabbitTemplate = new RabbitTemplate(connectionFactory);
        rabbitTemplate.setMessageConverter(jsonMessageConverter);
        return rabbitTemplate;
    }

    @Bean
    public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory,
            MessageConverter jsonMessageConverter
    ) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(jsonMessageConverter);
        return factory;
    }
}

